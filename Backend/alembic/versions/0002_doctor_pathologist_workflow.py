"""Introduce role accounts, patient ownership, and NPZ analyses."""
from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0002_doctor_pathologist_workflow"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="doctor"))
    op.add_column("users", sa.Column("assigned_doctor_id", sa.String(36), nullable=True))
    with op.batch_alter_table("users") as batch:
        batch.create_foreign_key("fk_users_assigned_doctor", "users", ["assigned_doctor_id"], ["id"], ondelete="SET NULL")
        batch.create_unique_constraint("uq_users_assigned_doctor", ["assigned_doctor_id"])

    op.create_table(
        "patients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_identifier", sa.String(120), nullable=False),
        sa.Column("created_by_pathologist_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("created_by_pathologist_id", "patient_identifier", name="uq_patient_pathologist_identifier"),
    )
    op.create_index("ix_patients_created_by_pathologist_id", "patients", ["created_by_pathologist_id"])

    # Preserve existing accounts and scans by turning legacy upload owners into
    # pathologists with a generated doctor account, then assigning each old scan
    # its own legacy patient record.
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, name, email, hashed_password, created_at, updated_at FROM users")).mappings().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        doctor_id = str(uuid.uuid4())
        connection.execute(sa.text(
            "INSERT INTO users (id,name,email,hashed_password,role,assigned_doctor_id,created_at,updated_at) "
            "VALUES (:id,:name,:email,:password,'doctor',NULL,:created,:updated)"
        ), {"id": doctor_id, "name": f"Legacy doctor for {row['name']}",
            "email": f"legacy-doctor-{row['id']}@invalid.local", "password": row["hashed_password"],
            "created": row["created_at"] or now, "updated": row["updated_at"] or now})
        connection.execute(sa.text("UPDATE users SET role='pathologist', assigned_doctor_id=:doctor WHERE id=:id"),
                           {"doctor": doctor_id, "id": row["id"]})

    op.drop_index("ix_scans_user_id", table_name="scans")
    with op.batch_alter_table("scans") as batch:
        batch.alter_column("user_id", new_column_name="pathologist_id", existing_type=sa.String(36), nullable=False)
        batch.add_column(sa.Column("patient_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("source_zip_path", sa.String(1024), nullable=True))
        batch.add_column(sa.Column("result_npz_path", sa.String(1024), nullable=True))
        batch.add_column(sa.Column("healthy_volume", sa.Float(), nullable=True))
        batch.add_column(sa.Column("penumbra_volume", sa.Float(), nullable=True))
        batch.add_column(sa.Column("core_volume", sa.Float(), nullable=True))
        batch.add_column(sa.Column("average_brain_height", sa.Float(), nullable=True))
        batch.add_column(sa.Column("per_slice_height", sa.Float(), nullable=True))

    old_scans = connection.execute(sa.text("SELECT id, pathologist_id FROM scans")).mappings().all()
    for scan in old_scans:
        patient_id = str(uuid.uuid4())
        connection.execute(sa.text(
            "INSERT INTO patients (id,patient_identifier,created_by_pathologist_id,created_at) "
            "VALUES (:id,:identifier,:pathologist,:created)"
        ), {"id": patient_id, "identifier": f"LEGACY-{scan['id']}",
            "pathologist": scan["pathologist_id"], "created": now})
        connection.execute(sa.text(
            "UPDATE scans SET patient_id=:patient, source_zip_path=:zip, status='failed' WHERE id=:id"
        ), {"patient": patient_id, "zip": f"uploads/{scan['id']}/source.zip", "id": scan["id"]})

    with op.batch_alter_table("scans") as batch:
        batch.alter_column("patient_id", existing_type=sa.String(36), nullable=False)
        batch.alter_column("source_zip_path", existing_type=sa.String(1024), nullable=False)
        batch.create_foreign_key("fk_scans_patient_id_patients", "patients", ["patient_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_scans_patient_id", ["patient_id"])
        batch.create_index("ix_scans_pathologist_id", ["pathologist_id"])
        batch.drop_column("core_volume_ml")
        batch.drop_column("penumbra_volume_ml")
        batch.alter_column("mismatch_volume_ml", new_column_name="mismatch_volume", existing_type=sa.Float(), nullable=True)
        batch.drop_column("volume_physical")
    # Existing single-image analysis artifacts do not match the NPZ contract.
    with op.batch_alter_table("scan_slices") as batch:
        batch.drop_column("core_mask_path")
        batch.drop_column("penumbra_mask_path")


def downgrade():
    raise RuntimeError("The role and patient workflow migration cannot be safely reversed after account assignment.")
