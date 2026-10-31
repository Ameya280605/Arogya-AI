"""Arogya AI — User & Role Domain Service.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Coordinates user account lifecycle, role authorization assignments, uniqueness
invariant checks, and operational audit event logging.
Transaction ownership strictly resides with the outer caller; UserService
never commits or rolls back sessions independently.
"""

from typing import Sequence
from uuid import UUID
from sqlalchemy.orm import Session

from backend.app.db.models import Role, User
from backend.app.repositories.user import RoleRepository, UserRepository
from backend.app.schemas.user import UserCreate, UserUpdate
from backend.app.services.audit import AuditService
from backend.app.services.exceptions import DuplicateEntityError, EntityNotFoundError


class UserService:
    """Domain service for managing user accounts and authorization roles."""

    def __init__(self, session: Session) -> None:
        """Initialize UserService with an active SQLAlchemy Session."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.audit_service = AuditService(session)

    # -------------------------------------------------------------------------
    # Role Operations
    # -------------------------------------------------------------------------

    def create_role(
        self,
        name: str,
        description: str | None = None,
        actor_id: UUID | None = None,
    ) -> Role:
        """Create a new authorization role, verifying name uniqueness."""
        clean_name = name.strip().lower()
        if self.role_repo.get_by_name(clean_name) is not None:
            raise DuplicateEntityError("Role", "name", clean_name)

        role = self.role_repo.create(name=clean_name, description=description)
        self.audit_service.record_event(
            event_type="role.created",
            action="create",
            actor_id=actor_id,
            resource_type="role",
            resource_id=str(role.id),
            description=f"Created authorization role '{role.name}'",
            event_metadata={"role_name": role.name},
        )
        return role

    def get_role(self, role_id: UUID) -> Role | None:
        """Retrieve a role by primary key UUID."""
        return self.role_repo.get_by_id(role_id)

    def get_role_by_name(self, name: str) -> Role | None:
        """Retrieve a role by unique canonical name."""
        return self.role_repo.get_by_name(name)

    def list_roles(self, limit: int = 100, offset: int = 0) -> Sequence[Role]:
        """Retrieve bounded list of roles."""
        return self.role_repo.list_roles(limit=limit, offset=offset)

    # -------------------------------------------------------------------------
    # User Operations
    # -------------------------------------------------------------------------

    def create_user(
        self,
        data: UserCreate,
        hashed_password: str | None = None,
        role_names: Sequence[str] | None = None,
        is_active: bool = True,
        actor_id: UUID | None = None,
    ) -> User:
        """Register a new user account, validating uniqueness and associating initial roles.

        Args:
            data: Validated UserCreate schema.
            hashed_password: Optional pre-computed password hash.
            role_names: Optional sequence of role names to link to user.
            is_active: Account active status flag (default True).
            actor_id: Optional UUID of the administrative actor performing creation.

        Returns:
            Newly created User entity.

        Raises:
            DuplicateEntityError: If username or email is already registered.
            EntityNotFoundError: If any specified role name does not exist.
        """
        # 1. Enforce unique handle
        if self.user_repo.get_by_username(data.username) is not None:
            raise DuplicateEntityError("User", "username", data.username)

        # 2. Enforce unique email
        if self.user_repo.get_by_email(data.email) is not None:
            raise DuplicateEntityError("User", "email", data.email)

        # 3. Resolve roles if requested
        resolved_roles: list[Role] = []
        if role_names:
            for rname in role_names:
                role = self.role_repo.get_by_name(rname)
                if role is None:
                    raise EntityNotFoundError("Role", rname)
                resolved_roles.append(role)

        # 4. Create user record
        user = self.user_repo.create(
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            hashed_password=hashed_password,
            is_active=is_active,
            roles=resolved_roles,
        )

        # 5. Record audit event (Strictly zero password/hash logging)
        self.audit_service.record_event(
            event_type="user.created",
            action="create",
            actor_id=actor_id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"Created user account '{user.username}'",
            event_metadata={
                "username": user.username,
                "email": user.email,
                "roles": [r.name for r in user.roles],
            },
        )
        return user

    def get_user(self, user_id: UUID) -> User | None:
        """Retrieve user by primary key UUID."""
        return self.user_repo.get_by_id(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        """Retrieve user by unique username."""
        return self.user_repo.get_by_username(username)

    def get_user_by_email(self, email: str) -> User | None:
        """Retrieve user by unique email."""
        return self.user_repo.get_by_email(email)

    def update_user(
        self,
        user_id: UUID,
        data: UserUpdate,
        hashed_password: str | None = None,
        actor_id: UUID | None = None,
    ) -> User:
        """Update user profile fields, verifying uniqueness if email changes."""
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundError("User", user_id)

        if data.email is not None and data.email.strip().lower() != user.email:
            existing_email = self.user_repo.get_by_email(data.email)
            if existing_email is not None and existing_email.id != user.id:
                raise DuplicateEntityError("User", "email", data.email)

        updated_user = self.user_repo.update(
            user=user,
            full_name=data.full_name,
            email=data.email,
            is_active=data.is_active,
            hashed_password=hashed_password,
        )

        self.audit_service.record_event(
            event_type="user.updated",
            action="update",
            actor_id=actor_id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"Updated user account '{user.username}'",
            event_metadata={"username": user.username},
        )
        return updated_user

    def assign_role(
        self,
        user_id: UUID,
        role_name: str,
        actor_id: UUID | None = None,
    ) -> User:
        """Assign an authorization role to a user."""
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundError("User", user_id)

        role = self.role_repo.get_by_name(role_name)
        if role is None:
            raise EntityNotFoundError("Role", role_name)

        self.user_repo.assign_role(user, role)
        self.audit_service.record_event(
            event_type="user.role_assigned",
            action="update",
            actor_id=actor_id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"Assigned role '{role.name}' to user '{user.username}'",
            event_metadata={"username": user.username, "role": role.name},
        )
        return user

    def remove_role(
        self,
        user_id: UUID,
        role_name: str,
        actor_id: UUID | None = None,
    ) -> User:
        """Remove an authorization role from a user."""
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundError("User", user_id)

        role = self.role_repo.get_by_name(role_name)
        if role is None:
            raise EntityNotFoundError("Role", role_name)

        self.user_repo.remove_role(user, role)
        self.audit_service.record_event(
            event_type="user.role_removed",
            action="update",
            actor_id=actor_id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"Removed role '{role.name}' from user '{user.username}'",
            event_metadata={"username": user.username, "role": role.name},
        )
        return user

    def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: bool | None = None,
    ) -> Sequence[User]:
        """Retrieve bounded list of users."""
        return self.user_repo.list_users(limit=limit, offset=offset, is_active=is_active)
