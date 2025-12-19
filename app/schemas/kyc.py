"""
KYC service schemas.
"""

from pydantic import BaseModel
from typing import Optional, List


class UploadDocumentRequest(BaseModel):
    driver_id: int
    document_type: str
    document_url: str


class DocumentResponse(BaseModel):
    id: int
    document_type: str
    document_url: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class KycStatusResponse(BaseModel):
    status: str
    documents_uploaded: int
    documents_approved: int
    documents_rejected: int
    documents_pending: int


class VerifyDocumentRequest(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None

