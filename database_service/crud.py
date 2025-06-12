from database_service.models import *
from database_service.log import setup_logger
logger = setup_logger(__name__)

def create_project(session,quest:dict):

    try:
        # Validate required fields
        required_fields = ['company_name', 'email', 'project_name', 'takeoff_division',
                           'sheet_uploaded', 'sheet_saved_at']

        missing_fields = [field for field in required_fields if field not in quest]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Create new project
        new_project = Project(**quest)
        session.add(new_project)
        session.commit()
        session.refresh(new_project)

        logger.info(f"New project created with id: {new_project.id}")
        return new_project

    except Exception as e:
        session.rollback()
        raise Exception(f"Failed to create project: {str(e)}")


def create_project_status(session, project_status_data):
    """Insert a new row in the Project_Status table."""
    try:
        project_status_data['status']="ML_process_start"
        new_status = Project_Status(
            **project_status_data
        )
        session.add(new_status)
        session.commit()
        session.refresh(new_status)
        logger.info(f"New project status created with id: {new_status.id}")
        return new_status
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating project status: {str(e)}")
        raise e


def create_sheet_info(session, sheet_data: dict):
    try:
        # Check if project exists
        if 'project_id' in sheet_data:
            project_id = sheet_data['project_id']
            if not isinstance(project_id, uuid.UUID):
                project_id = uuid.UUID(str(project_id))

            project = session.query(Project).filter(Project.id == project_id).first()
            logger.info(f"Project found: {project is not None}")

            if not project:
                logger.error(f"No project found with ID: {project_id}")
                raise ValueError(f"No project found with ID: {project_id}")

        # Create sheet
        new_sheet = Sheets_Info(**sheet_data)
        session.add(new_sheet)

        # Log pre-commit state
        logger.info(f"Sheet added to session with ID: {new_sheet.id}")

        # Commit transaction
        session.commit()

        # Log post-commit state
        logger.info(f"Sheet committed to database with ID: {new_sheet.id}")

        # Verify sheet exists after commit for debug
        # new_sheet_id = uuid.UUID(str(new_sheet.id))
        # verification = session.query(Sheets_Info).filter(Sheets_Info.id == new_sheet_id).first()
        # logger.info(f"Verification query result: {verification is not None}")

        session.refresh(new_sheet)
        # logger.info(f"Sheet refreshed from database: {new_sheet.__dict__}")
        return new_sheet
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating sheet info: {str(e)}")
        # Log the full exception traceback for more details
        import traceback
        logger.error(traceback.format_exc())
        raise


def create_annotation_info(session, annotation_data:dict):
    try:
        new_annotation = Annotation_Info(**annotation_data)
        session.add(new_annotation)
        session.commit()
        session.refresh(new_annotation)
        logger.info(f"New annotation info created with id: {new_annotation.id}")
        return new_annotation
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating annotation info: {str(e)}")
        raise e


def create_dynamic_table(session,engine,dynamic_table_name):
    """
    Create a dynamic table for the project.
    Returns the ORM model for the dynamic table.
    """
    #dynamic_table_name = f"project_{project_id}"
    DynamicModel = create_dynamic_sheet_info(dynamic_table_name)
    # Create the table in the database if it doesn't exist
    DynamicModel.__table__.create(bind=engine, checkfirst=True)
    logger.info(f"Dynamic table '{dynamic_table_name}' created.")
    return DynamicModel


def update_project(session, filter_criteria,update_data):
    """
    Update the project row's sheet_info JSON column by adding or updating the entry for sheet_key.
    """
    try:
        result = session.query(Project).filter_by(**filter_criteria).update(
            update_data, synchronize_session="fetch"
        )
        session.commit()
        logger.info(f"Updated {result} projects matching criteria: {filter_criteria}")
        return result
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating projects: {str(e)}")
        raise e

def update_project_status(session,filter_criteria:dict,update_status:dict)->None:
    # current_status = session.query(Project_Status).filter(Project_Status.project_id == project_id).first()
    try:
        result = session.query(Project_Status).filter_by(**filter_criteria).update(update_status, synchronize_session="fetch")  # Assuming there's a status column
        session.commit()
        if result == 0:
            logger.warning(f"No records matched the criteria: {filter_criteria}")
        else:
            logger.info(f"Updated {result} project status records")
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating project status: {str(e)}")
        raise e

def insert_sheet_data(session, sheet_data_dict, identifier=None, identifier_column='id'):
    """
    Insert or update sheet data in the dynamic table.
    Parameters:
        session: SQLAlchemy session
        sheet_data_dict: Dictionary containing the data to insert/update
        identifier: Value to identify existing record (if None, creates new record)
        identifier_column: Column name to use for identifying existing record (default: 'id')
    Returns:
        The created or updated record
    """
    try:
        if identifier is not None:
            # Try to find existing record
            existing_record = session.query(Sheets_Info).filter(
                getattr(Sheets_Info, identifier_column) == identifier
            ).first()

            if existing_record:
                # Update existing record
                for key, value in sheet_data_dict.items():
                    setattr(existing_record, key, value)
                logger.debug(f"Updated existing record with {identifier_column}: {identifier}")
                record = existing_record
            else:
                # Create new record if not found
                record = Sheets_Info(**sheet_data_dict)
                session.add(record)
                logger.debug(f"Created new record as no existing record found with {identifier_column}: {identifier}")
        else:
            # Create new record
            record = Sheets_Info(**sheet_data_dict)
            session.add(record)
            logger.debug("Created new record in dynamic table")

        session.commit()
        session.refresh(record)
        return record

    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting/updating data: {str(e)}")
        raise e


def row_to_dict(row) -> dict:
    """
    Convert an ORM object to a plain dictionary of column names -> values.
    (Skips SQLAlchemy internal attributes.)
    """
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
    }


def get_projects(session, skip: int = 0, limit: int = 100,filter_criteria:dict=None) -> list:
    if filter_criteria is None:
        return session.query(Project).offset(skip).limit(limit).all()
    else:
        return session.query(Project).filter_by(**filter_criteria).all()

def get_project_statuses(session, skip: int = 0, limit: int = 100):
    return session.query(Project_Status).offset(skip).limit(limit).all()

def get_project_by_id(session, project_id: int):
    return session.query(Project).filter_by(Project.id==project_id).first()

def get_project_status_by_id(session, project_status_id):
    return session.query(Project_Status).filter_by(Project_Status.id==project_status_id).first()

def get_project_by_condition(session, project_name: str):
    return session.query(Project).filter_by(Project.project_name==project_name).all()

def get_sheet_info_table(session, sheet_info_dict:dict = None)->list:
    if sheet_info_dict is None:
        return session.query(Sheets_Info).limit(100).all()
    else:
        return session.query(Sheets_Info).filter_by(**sheet_info_dict).all()

def get_annotation_table(session, annotation_data_dict:dict=None)->list:
    if annotation_data_dict is None:
        return session.query(Annotation_Info).limit(100).all()
    else:
        return session.query(Annotation_Info).filter_by(**annotation_data_dict).all()

def delete_project_by_id(session, project_id: int):
    session.query(Project).filter_by(id=project_id).delete()
    session.commit()

def delete_project_by_condition(session,filter_criteria:dict):
    try:
        result = session.query(Project).filter_by(**filter_criteria).delete(synchronize_session="fetch")
        session.commit()
        if result > 0:
            logger.info(f"Successfully deleted {result} project(s) matching criteria")
        else:
            logger.warning(f"No projects found matching criteria: {filter_criteria}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error delete sheet info data: {str(e)}")
        raise e


def delete_project_status_by_id(session, project_status_id:int):
    session.query(Project_Status).filter_by(id=project_status_id).delete()
    session.commit()

def delete_project_status_by_condition(session, filter_criteria:dict):
    try:
        session.query(Project_Status).filter_by(**filter_criteria).delete(synchronize_session="fetch")
    except Exception as e:
        session.rollback()
        logger.error(f"Error delete project status data: {str(e)}")
        raise e

def delete_sheet_info_by_id(session, sheet_info_id:int):
    session.query(Sheets_Info).filter_by(id=sheet_info_id).delete()
    session.commit()

def delete_sheet_info_by_condition(session, filter_criteria:dict):
    try:
        result = session.query(Sheets_Info).filter_by(**filter_criteria).delete(synchronize_session="fetch")
        session.commit()
        if result > 0:
            logger.info(f"Successfully deleted {result} sheet into matching criteria")
        else:
            logger.warning(f"No sheet info found matching criteria: {filter_criteria}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error delete sheet info data: {str(e)}")
        raise e

def delete_annotation_by_condition(session, filter_criteria:dict):
    try:
        result = session.query(Annotation_Info).filter_by(**filter_criteria).delete(synchronize_session="fetch")
        session.commit()
        if result > 0:
            logger.info(f"Successfully deleted {result} annotation into matching criteria")
        else:
            logger.warning(f"No annotation info found matching criteria: {filter_criteria}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error delete annotation data: {str(e)}")
        raise e

# def get_sheet_info_table(session,dynamic_table_name):
#     """
#     Create a dynamic table for the project.
#     Returns the ORM model for the dynamic table.
#     """
#     inspector = inspect(session.bind)
#     if dynamic_table_name not in inspector.get_table_names():
#         logger.info(f"Dynamic table '{dynamic_table_name}' not found.")
#         raise HTTPException(status_code=404, detail=f"Table '{dynamic_table_name}' not found")
#     else:
#         DynamicModel = create_dynamic_table(dynamic_table_name)
#         return session.query(DynamicModel).all()

