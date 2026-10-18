from pathlib import Path

from db.repository import initialize_database


CRITERIA = [
    (
        "Technical Capability",
        "Architecture, interoperability (HL7 v2, FHIR R4, DICOM, ABDM), scalability and performance evidence, high availability and disaster recovery, clinical decision support and clinical fit.",
        30,
        10,
    ),
    (
        "Implementation Plan",
        "Timeline against the 9-month target, phased milestones with acceptance criteria, named team and roles, training, data migration approach, and risk plan.",
        20,
        10,
    ),
    (
        "Commercial Value",
        "Pricing clarity, 5-year total cost, itemised price table, assumptions, exclusions, and hidden costs.",
        20,
        10,
    ),
    (
        "Security & Compliance",
        "Certifications, encryption, access control, audit logging and retention, DPDP Act 2023 alignment, India data residency, and breach notification.",
        20,
        10,
    ),
    (
        "Support & Experience",
        "Support model and SLAs, 24x7 coverage, similar hospital deployments, and named references.",
        10,
        10,
    ),
]


def seed_database(db_path: str | Path | None = None) -> None:
    from db.repository import get_connection

    connection = get_connection(db_path)
    try:
        initialize_database(connection)
        count = connection.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
        if count == 0:
            connection.executemany(
                "INSERT INTO evaluation_criteria (name, description, weight, max_score) VALUES (?, ?, ?, ?)",
                CRITERIA,
            )
            connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    seed_database()
