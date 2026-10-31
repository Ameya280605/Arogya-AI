"""Arogya AI — User and Role Repositories.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Encapsulates database operations for users, roles, and user_roles association.
"""

from typing import Sequence
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.db.models import Role, User
from backend.app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Data access repository for authorization roles."""

    def get_by_id(self, role_id: UUID) -> Role | None:
        """Retrieve a role by its primary key UUID."""
        return self.session.get(Role, role_id)

    def get_by_name(self, name: str) -> Role | None:
        """Retrieve a role by its unique canonical name."""
        stmt = select(Role).where(Role.name == name.strip().lower())
        return self.session.scalar(stmt)

    def create(self, name: str, description: str | None = None) -> Role:
        """Instantiate and persist a new role record."""
        role = Role(name=name.strip().lower(), description=description)
        self.session.add(role)
        self.session.flush()
        return role

    def list_roles(self, limit: int = 100, offset: int = 0) -> Sequence[Role]:
        """Retrieve bounded list of roles ordered by name."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = (
            select(Role)
            .order_by(Role.name.asc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()


class UserRepository(BaseRepository[User]):
    """Data access repository for user accounts and role associations."""

    def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a user by their primary key UUID with eager-loaded roles."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
        )
        return self.session.scalar(stmt)

    def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by their unique username."""
        stmt = (
            select(User)
            .where(User.username == username.strip())
            .options(selectinload(User.roles))
        )
        return self.session.scalar(stmt)

    def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by their unique email address."""
        stmt = (
            select(User)
            .where(User.email == email.strip().lower())
            .options(selectinload(User.roles))
        )
        return self.session.scalar(stmt)

    def create(
        self,
        username: str,
        email: str,
        full_name: str,
        hashed_password: str | None = None,
        is_active: bool = True,
        roles: Sequence[Role] | None = None,
    ) -> User:
        """Instantiate and persist a new user record with optional role assignments."""
        user = User(
            username=username.strip(),
            email=email.strip().lower(),
            full_name=full_name.strip(),
            hashed_password=hashed_password,
            is_active=is_active,
        )
        if roles:
            user.roles.extend(roles)

        self.session.add(user)
        self.session.flush()
        return user

    def update(
        self,
        user: User,
        full_name: str | None = None,
        email: str | None = None,
        is_active: bool | None = None,
        hashed_password: str | None = None,
    ) -> User:
        """Update mutable fields on an existing user instance."""
        if full_name is not None:
            user.full_name = full_name.strip()
        if email is not None:
            user.email = email.strip().lower()
        if is_active is not None:
            user.is_active = is_active
        if hashed_password is not None:
            user.hashed_password = hashed_password

        self.session.flush()
        return user

    def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: bool | None = None,
    ) -> Sequence[User]:
        """Retrieve a bounded list of users with eager-loaded roles."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = select(User).options(selectinload(User.roles))

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        stmt = (
            stmt.order_by(User.created_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def count_users(self, is_active: bool | None = None) -> int:
        """Count total user records matching criteria."""
        stmt = select(func.count(User.id))
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        return self.session.scalar(stmt) or 0

    def assign_role(self, user: User, role: Role) -> None:
        """Assign a role to a user if not already linked."""
        if role not in user.roles:
            user.roles.append(role)
            self.session.flush()

    def remove_role(self, user: User, role: Role) -> None:
        """Remove a role assignment from a user."""
        if role in user.roles:
            user.roles.remove(role)
            self.session.flush()
