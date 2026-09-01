import logging
import os
import sqlite3

from sqlmodel import SQLModel, create_engine, Session, select
from app.config import settings
from app.models.preset import Preset
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.artist import Artist
from app.models.lora import Lora
from app.models.lora_source import LoraSource
from app.models.rule import RuleFile
from app.models.setting import AppSetting
from app.models.history import GenerationHistory

logger = logging.getLogger(__name__)

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)


def ensure_data_dirs() -> None:
    """Create ImageForge-owned data directories (generated images etc.)."""
    for d in [settings.GENERATED_DIR]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:  # pragma: no cover
            logger.warning(f"Failed to create data dir {d}: {e}")


def _migrate_legacy_sqlite(database_url: str | None = None) -> None:
    """Lightweight migrations for legacy SQLite schemas.

    - Only touches tables that actually exist: on a fresh database (no `loras`
      table yet) this is a strict no-op — `create_all()` runs afterwards.
    - `loras.is_enabled` was NOT NULL in older databases while the ORM now
      declares it Optional — INSERTs then fail with NOT NULL constraint
      (POST /api/loras 500). Rebuild the table with a nullable column.
    - `loras.source_path` column added for source-scan imports.
    """
    url = database_url or settings.DATABASE_URL
    if "sqlite" not in url:
        return
    path = url.replace("sqlite:///", "").split("?")[0]
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "loras" not in tables:
            return  # fresh DB: nothing to migrate (create_all will build the schema)

        # -- 1. loras.is_enabled NOT NULL -> nullable with default 0 ----------
        cols = {r[1]: r for r in cur.execute("PRAGMA table_info(loras)").fetchall()}
        if "is_enabled" in cols and cols["is_enabled"][3] == 1:  # notnull == 1
            _rebuild_loras_table(cur)
            conn.commit()
            logger.info("Migrated loras.is_enabled to nullable (legacy NOT NULL dropped)")

        # -- 2. loras.source_path column --------------------------------------
        cols = {r[1]: r for r in cur.execute("PRAGMA table_info(loras)").fetchall()}
        if "source_path" not in cols:
            cur.execute("ALTER TABLE loras ADD COLUMN source_path TEXT")
            conn.commit()
            logger.info("Added loras.source_path column")
    except Exception as e:  # pragma: no cover
        logger.error(f"Schema migration failed: {e}")
        raise
    finally:
        conn.close()


def _rebuild_loras_table(cur: sqlite3.Cursor) -> None:
    """SQLite table rebuild (12-step ALTER) to drop NOT NULL on is_enabled."""
    cols = cur.execute("PRAGMA table_info(loras)").fetchall()  # (cid,name,type,notnull,dflt,pk)
    defs = []
    for cid, name, ctype, notnull, dflt, pk in cols:
        if name == "is_enabled":
            defs.append(f'"{name}" {ctype or "BOOLEAN"} DEFAULT 0')
        else:
            nn = " NOT NULL" if notnull else ""
            df = f" DEFAULT {dflt}" if dflt is not None else ""
            pk_part = " PRIMARY KEY" if pk else ""
            defs.append(f'"{name}" {ctype or ""}{nn}{df}{pk_part}')
    colnames = ", ".join(f'"{c[1]}"' for c in cols)
    cur.execute("ALTER TABLE loras RENAME TO loras_legacy")
    cur.execute(f"CREATE TABLE loras ({', '.join(defs)})")
    cur.execute(f"INSERT INTO loras ({colnames}) SELECT {colnames} FROM loras_legacy")
    cur.execute("DROP TABLE loras_legacy")
    # recreate indexes that SQLModel declares on loras
    cur.execute("CREATE INDEX IF NOT EXISTS ix_loras_name ON loras (name)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_loras_filename ON loras (filename)")


def init_db():
    ensure_data_dirs()
    _migrate_legacy_sqlite()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # 1. Synchronize SQLite AppSetting table into memory settings
        db_settings = session.exec(select(AppSetting)).all()
        from app.config import EDITABLE_SETTING_KEYS
        for s in db_settings:
            if s.key in EDITABLE_SETTING_KEYS and hasattr(settings, s.key):
                val = s.value
                field_type = type(getattr(settings, s.key))
                if field_type == bool:
                    val = str(val).lower() in ("true", "1", "yes")
                elif field_type == int:
                    try:
                        val = int(val)
                    except ValueError:
                        val = getattr(settings, s.key)
                setattr(settings, s.key, val)

        # 2. Seed default preset
        stmt = select(Preset).where(Preset.is_default == True)
        default_preset = session.exec(stmt).first()
        if not default_preset:
            preset = Preset(
                name="标准 Anima-2.9B (默认)",
                positive_prefix="",
                default_negative="lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry",
                is_default=True
            )
            session.add(preset)
            session.commit()

        # 3. Seed initial sample artists with @artist format
        stmt_art = select(Artist)
        first_art = session.exec(stmt_art).first()
        if not first_art:
            sample_artists = [
                Artist(name="Mika Pikazo", tags="@mika_pikazo", category="高饱和/活力", is_favorite=True, is_custom=False, description="色彩鲜明、高对比度、流行感十足的二次元插画风格"),
                Artist(name="Tiv", tags="@tiv", category="精致/光影", is_favorite=True, is_custom=False, description="精细的眼部刻画、清透的高光与细腻的五官线条"),
                Artist(name="Range Murata (村田莲尔)", tags="@range_murata", category="复古/机械", is_favorite=False, is_custom=False, description="复古未来主义、机械质感与独特人物轮廓"),
                Artist(name="WLOP", tags="@wlop", category="厚涂/氛围", is_favorite=True, is_custom=False, description="史诗感光影、厚涂质感与写实二次元融合风格"),
                Artist(name="Kantoku (カントク)", tags="@kantoku", category="校园/萌系", is_favorite=False, is_custom=False, description="标志性格子图案、明亮光影与跃动少女"),
                Artist(name="fkey", tags="@fkey", category="暗黑/机能", is_favorite=False, is_custom=False, description="高冷色调、机能风与戏剧性明暗对比"),
            ]
            for a in sample_artists:
                session.add(a)
            session.commit()

        # 4. Seed initial sample rule
        stmt_rule = select(RuleFile)
        first_rule = session.exec(stmt_rule).first()
        if not first_rule:
            rule = RuleFile(
                name="Anima 2.9B 提示词习惯参考",
                file_type=".md",
                content="""# Anima-2.9B 提示词指南
- 画师格式：使用 `@artist_name` 格式（如 `@mika_pikazo`）。
- 角色与动作绑定：多人场景必须使用自然语言明确谁穿什么、谁对谁做什么。
- 采样推荐：Euler 采样器 + sgm_uniform / beta 调度器，分辨率 1024x1536 或 1152x1536。
""",
                is_enabled=True,
                sort_order=1
            )
            session.add(rule)
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session
