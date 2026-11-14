import sys
import logging
from backend.app.database import SessionLocal
from backend.app.services.projection_service import rebuild_projections, verify_projections_integrity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rebuild_projections")


def main():
    logger.info("Starting local administrative CQRS projection rebuild...")
    db = SessionLocal()
    try:
        result = rebuild_projections(db)
        db.commit()
        if not verify_projections_integrity(db):
            logger.error(f"Projection rebuild failed integrity verification: {result}")
            sys.exit(1)
        logger.info(f"Projection rebuild completed successfully: {result}")
    except Exception as e:
        db.rollback()
        logger.error(f"Projection rebuild aborted due to error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
