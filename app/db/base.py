from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import DateTime, func, UUID as SQLUUID, text    
from sqlalchemy.orm import Mapped, mapped_column
import uuid



class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore
        return cls.__name__.lower()

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("uuid_generate_v4()"),
        index=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


