from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.rule import RuleFile, RuleFileCreate, RuleFileUpdate, RuleFileRead

router = APIRouter(prefix="/rules", tags=["rules"])

@router.get("", response_model=List[RuleFileRead])
def list_rules(session: Session = Depends(get_session)):
    stmt = select(RuleFile).order_by(RuleFile.sort_order)
    return session.exec(stmt).all()

@router.post("", response_model=RuleFileRead)
def create_rule(rule_in: RuleFileCreate, session: Session = Depends(get_session)):
    rule = RuleFile.model_validate(rule_in)
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule

@router.post("/upload", response_model=RuleFileRead)
async def upload_rule_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Uploads a .md, .txt, or .yaml rule file and parses into database."""
    filename = file.filename or "uploaded_rule.md"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".md"
    
    if ext not in [".md", ".txt", ".yaml", ".yml"]:
        raise HTTPException(status_code=400, detail="仅支持 .md, .txt, .yaml 格式的说明文件")

    content_bytes = await file.read()
    try:
        content_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_text = content_bytes.decode("gbk", errors="ignore")

    name = filename.rsplit(".", 1)[0]
    rule = RuleFile(
        name=name,
        file_type=ext,
        content=content_text,
        is_enabled=True,
        sort_order=10
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule

@router.put("/{rule_id}", response_model=RuleFileRead)
def update_rule(
    rule_id: int,
    rule_in: RuleFileUpdate,
    session: Session = Depends(get_session)
):
    rule = session.get(RuleFile, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则文件不存在")
    data = rule_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(rule, key, value)
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule

@router.delete("/{rule_id}")
def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    rule = session.get(RuleFile, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则文件不存在")
    session.delete(rule)
    session.commit()
    return {"status": "ok"}
