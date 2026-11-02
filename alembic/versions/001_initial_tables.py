"""Initial database schema for children schedule bot

Revision ID: 001_initial_tables
Revises: 
Create Date: 2026-11-02 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('full_name', sa.String(length=128), server_default='', nullable=False),
        sa.Column('role', sa.String(length=32), server_default='parent', nullable=False),
        sa.Column('timezone', sa.String(length=64), server_default='Europe/Moscow', nullable=False),
        sa.Column('is_notifications_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('quiet_hours_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('quiet_hours_start', sa.Time(), nullable=True),
        sa.Column('quiet_hours_end', sa.Time(), nullable=True),
        sa.Column('morning_digest_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('morning_digest_time', sa.Time(), server_default='08:00:00', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. children
    op.create_table(
        'children',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('parent_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('color_emoji', sa.String(length=16), server_default='👧', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_children_parent_id'), 'children', ['parent_id'], unique=False)

    # 3. locations
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('address', sa.String(length=255), server_default='', nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_locations_user_id'), 'locations', ['user_id'], unique=False)

    # 4. activities
    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('child_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=50), server_default='Другое', nullable=False),
        sa.Column('icon', sa.String(length=16), server_default='📌', nullable=False),
        sa.Column('teacher_name', sa.String(length=100), nullable=True),
        sa.Column('teacher_phone', sa.String(length=50), nullable=True),
        sa.Column('items_to_bring', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['child_id'], ['children.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_child_id'), 'activities', ['child_id'], unique=False)

    # 5. schedules
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('is_recurring', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('specific_date', sa.Date(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('is_cancelled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_completed', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schedules_activity_id'), 'schedules', ['activity_id'], unique=False)

    # 6. reminder_settings
    op.create_table(
        'reminder_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('remind_1_day', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('remind_2_hours', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('remind_30_min', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('remind_10_min', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notify_parent', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notify_child', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('custom_minutes_before', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('activity_id')
    )

    # 7. notification_logs
    op.create_table(
        'notification_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=True),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('notification_type', sa.String(length=32), nullable=False),
        sa.Column('target_datetime', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='sent', nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notification_dedup', 'notification_logs', ['schedule_id', 'notification_type', 'target_datetime', 'user_id'])
    op.create_index(op.f('ix_notification_logs_user_id'), 'notification_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('notification_logs')
    op.drop_table('reminder_settings')
    op.drop_table('schedules')
    op.drop_table('activities')
    op.drop_table('locations')
    op.drop_table('children')
    op.drop_table('users')
