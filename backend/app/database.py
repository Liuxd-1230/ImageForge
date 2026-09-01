from sqlmodel import SQLModel, create_engine, Session, select
from app.config import settings
from app.models.preset import Preset
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.artist import Artist
from app.models.lora import Lora
from app.models.rule import RuleFile
from app.models.setting import AppSetting
from app.models.history import GenerationHistory

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)

def init_db():
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
