# from genson.schema.strategies import Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
# from pydantic import BaseModel
# from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class Project_Status(Base):
    __tablename__ = 'project_status'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), index=True) # project id
    ann_project_dir = Column(String, nullable=True) # s3 bucket address of the annotation data
    project_name = Column(String, nullable=False)
    status = Column(String, nullable=False)


class Project(Base):
    __tablename__ = 'project'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    company_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    takeoff_division = Column(String, nullable=False)
    project_description = Column(String, nullable=True)
    project_address = Column(String, nullable=True)
    sheet_uploaded = Column(TIMESTAMP, nullable=False)
    sheet_saved_at = Column(String, nullable=False)
    takeoff_delivery = Column(String, nullable=True)
    takeoff_deliver_at = Column(TIMESTAMP, nullable=True)
    sheets = relationship("Sheets_Info", back_populates="project")
    annotations = relationship("Annotation_Info", back_populates="project")

class Sheets_Info(Base):
    __tablename__ = 'sheets_info'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True,default=uuid.uuid4 )
    project_id = Column(UUID(as_uuid=True), ForeignKey(Project.id), nullable=False, index=True)
    sheet_number = Column(Integer, nullable=True)
    drawing_number = Column(String, nullable=True)
    drawing_title = Column(String, nullable=True)
    title_block_content = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    pic_path = Column(String, nullable=True)
    sheet_text_block = Column(JSON,default=dict, server_default=text("'{}'"), nullable=True)
    sheet_text = Column(JSON,default=list, server_default=text("'[]'"), nullable=True)
    ml_prediction = Column(JSON, default=dict, server_default=text("'{}'"), nullable=True)
    have_drawing = Column(Boolean, nullable=True)
    have_objects = Column(Boolean, nullable=True)
    have_schedule_table = Column(Boolean, nullable=True)
    have_symbol_legend = Column(Boolean, nullable=True)
    have_tag_target = Column(Boolean, nullable=True)
    project = relationship("Project", back_populates="sheets")
    annotations = relationship("Annotation_Info", back_populates="sheet")

class Annotation_Info(Base):
    __tablename__ = 'annotation_info'
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    sheet_id = Column(UUID(as_uuid=True), ForeignKey(Sheets_Info.id), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey(Project.id), nullable=False, index=True)
    image_dpi = Column(Integer, default=72, nullable=True)
    object_name = Column(String, nullable=True)
    location = Column(JSON, default=list, server_default=text("'[]'"), nullable=True)
    have_tag = Column(Boolean, default=False, nullable=True)
    tag = Column(String, nullable=True)
    sheet = relationship("Sheets_Info", back_populates="annotations")
    project = relationship("Project", back_populates="annotations")


def create_dynamic_sheet_info(table_name):
    return type(
        table_name,
        (Base,),  # Inherit from Base
        {
            "__tablename__": table_name,
            "id": Column(UUID(as_uuid=True), primary_key=True,autoincrement=True ,index=True),
            "sheet_number": Column(Integer, nullable=True),
            "project_id": Column(Integer, index=True), # project_id from project.id
            "drawing_number": Column(String, default="",nullable=True),
            "drawing_title": Column(String, default="Unkown", nullable=True),
            "title_block_content": Column(String, nullable=True),
            "pdf_path": Column(String, default = "",nullable=True),
            "pic_path": Column(String, default = "" ,nullable=True),
            "ml_precision": Column(JSON, default=dict,server_default=text("'{}'"),nullable=True),
            "annotations": Column(JSON,default=dict,server_default=text("'{}'"), nullable=True),
            "have_drawing": Column(Boolean, server_default=text("false"),default=False),
            "have_objects": Column(Boolean, server_default=text("false"),default=False),
            "have_symbol_legend": Column(Boolean, server_default=text("false"),default=False),
            "have_schedule_table": Column(Boolean, server_default=text("false"),default=False),
            "have_tag_target": Column(Boolean, server_default=text("false"),default=False)
        },
    )

