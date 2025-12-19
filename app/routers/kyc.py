"""
KYC router: Document upload and verification endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.kyc_service import KycService
from app.schemas.kyc import (
    UploadDocumentRequest,
    DocumentResponse,
    KycStatusResponse,
    VerifyDocumentRequest,
)

router = APIRouter()


@router.post("/documents/upload", response_model=DocumentResponse)
def upload_document(
    payload: UploadDocumentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = KycService(db)
    
    try:
        doc = service.upload_document(
            driver_id=payload.driver_id,
            agency_id=payload.agency_id,
            document_type=payload.document_type,
            document_url=payload.document_url,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return DocumentResponse(
        id=doc.id,
        document_type=doc.document_type,
        document_url=doc.document_url,
        status=doc.status,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/documents", response_model=list[DocumentResponse])
def get_documents(
    driver_id: int = None,
    agency_id: int = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = KycService(db)
    
    docs = service.get_documents(driver_id=driver_id, agency_id=agency_id)
    
    return [
        DocumentResponse(
            id=doc.id,
            document_type=doc.document_type,
            document_url=doc.document_url,
            status=doc.status,
            created_at=doc.created_at.isoformat(),
        )
        for doc in docs
    ]


@router.get("/status", response_model=KycStatusResponse)
def get_kyc_status(
    driver_id: int = None,
    agency_id: int = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = KycService(db)
    
    status_data = service.get_kyc_status(driver_id=driver_id, agency_id=agency_id)
    
    return KycStatusResponse(**status_data)


@router.post("/documents/{document_id}/verify")
def verify_document(
    document_id: int,
    payload: VerifyDocumentRequest,
    request: Request,
    verifier_user_id: int = 1,  # In production, get from JWT token
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = KycService(db)
    
    try:
        doc = service.verify_document(
            document_id=document_id,
            verifier_user_id=verifier_user_id,
            approved=payload.approved,
            rejection_reason=payload.rejection_reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {"trace_id": trace_id, "status": "success", "document_status": doc.status}

