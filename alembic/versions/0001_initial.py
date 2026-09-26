from alembic import op
import sqlalchemy as sa
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("users",sa.Column("id",sa.String(36),primary_key=True),sa.Column("name",sa.String(120),nullable=False),sa.Column("email",sa.String(320),nullable=False,unique=True),sa.Column("hashed_password",sa.String(255),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_users_email","users",["email"],unique=True)
    op.create_table("scans",sa.Column("id",sa.String(36),primary_key=True),sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("original_filename",sa.String(255),nullable=False),sa.Column("scan_type",sa.String(8),nullable=False),sa.Column("status",sa.String(16),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("total_slices",sa.Integer,nullable=False),sa.Column("core_volume_ml",sa.Float),sa.Column("penumbra_volume_ml",sa.Float),sa.Column("mismatch_volume_ml",sa.Float),sa.Column("mismatch_ratio",sa.Float),sa.Column("volume_physical",sa.Boolean,nullable=False))
    op.create_index("ix_scans_user_id","scans",["user_id"])
    op.create_table("scan_slices",sa.Column("id",sa.String(36),primary_key=True),sa.Column("scan_id",sa.String(36),sa.ForeignKey("scans.id",ondelete="CASCADE"),nullable=False),sa.Column("slice_index",sa.Integer,nullable=False),sa.Column("original_image_path",sa.String(1024),nullable=False),sa.Column("core_mask_path",sa.String(1024)),sa.Column("penumbra_mask_path",sa.String(1024)),sa.Column("pixel_spacing_x",sa.Float),sa.Column("pixel_spacing_y",sa.Float),sa.Column("slice_thickness",sa.Float),sa.UniqueConstraint("scan_id","slice_index"))
    op.create_index("ix_scan_slices_scan_id","scan_slices",["scan_id"])
def downgrade():
    op.drop_table("scan_slices"); op.drop_table("scans"); op.drop_index("ix_users_email",table_name="users"); op.drop_table("users")
