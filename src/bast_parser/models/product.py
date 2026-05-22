from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Union

class Picture(BaseModel):
    url: HttpUrl
    main: bool

class Documents(BaseModel):
    documentsUserManual: Optional[HttpUrl] = None
    documentsCertificatesTrts: Optional[HttpUrl] = None
    documentsCertificateDeclaration037: Optional[HttpUrl] = None
    documentsCertificateCertification: Optional[HttpUrl] = None
    documentsBimModelsRevit: Optional[HttpUrl] = None
    documentsBimModelsAutocad: Optional[HttpUrl] = None

class Offer(BaseModel):
    id: str
    url: Optional[HttpUrl] = None
    removed: Optional[str] = None
    vendorCode: Union[str, int]
    model: str
    pictures: List[Picture] = []
    documents: Optional[Documents] = None

class Subsection(BaseModel):
    uuidSubsection: str
    nameSubsection: str
    offer: Optional[Offer] = None

class Section(BaseModel):
    uuidSection: str
    nameSection: str
    subsections: List[Subsection] = []

class CatalogResponse(BaseModel):
    catalog: List[Section]