from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint, Index
from enum import Enum


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthToken(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    provider: str = Field(default="google")
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    token_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class File(SQLModel, table=True):
    __table_args__ = (
        Index("ix_file_user_sha256", "user_id", "sha256"),  # Deduplication lookups
        Index("ix_file_created", "created_at"),  # Sorting/pagination
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    drive_file_id: Optional[str] = Field(default=None, index=True)
    name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    local_path: Optional[str] = None
    sha256: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Membership(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "user_id", "room_id", name="uq_user_room"
        ),  # One membership per user per room
        Index(
            "ix_membership_room_role", "room_id", "role"
        ),  # Lookup admins/owners of a room
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    room_id: int = Field(index=True, foreign_key="room.id")

    class Role(str, Enum):
        owner = "owner"
        admin = "admin"
        editor = "editor"
        viewer = "viewer"

    role: "Membership.Role" = Field(default=Role.owner)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FileRoomLink(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "file_id", "room_id", name="uq_file_room"
        ),  # One link per file per room
        Index("ix_link_room_file", "room_id", "file_id"),  # Lookup files in a room
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(index=True, foreign_key="file.id")
    room_id: int = Field(index=True, foreign_key="room.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    __table_args__ = (
        Index("ix_audit_created", "created_at"),  # Time-series queries
        Index("ix_audit_room_action", "room_id", "action"),  # Room activity reports
        Index("ix_audit_actor_created", "actor_user_id", "created_at"),  # User activity
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_user_id: Optional[int] = Field(
        default=None, index=True, foreign_key="user.id"
    )
    action: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    room_id: Optional[int] = Field(default=None, index=True, foreign_key="room.id")
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
