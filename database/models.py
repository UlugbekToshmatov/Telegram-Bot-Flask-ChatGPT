from sqlalchemy import Text, String, Integer, DateTime, func, ForeignKey, Boolean, Numeric, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[DateTime] = mapped_column(DateTime, default=None, nullable=True)


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(15), nullable=False)
    privileges: Mapped[str] = mapped_column(String(255), nullable=False)

    # Adding the reverse relationship to users to access all users associated with one type of role using role.users
    users: Mapped["User"] = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # nullable because users may request from web API too
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=True, unique=True)
    # Telegram username while adding new admins in order to find and contact admins quickly
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    surname: Mapped[str] = mapped_column(String(64), nullable=True)
    # Password is for admins to be able to manage their jobs through web APIs also
    password: Mapped[str] = mapped_column(String(64), nullable=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("role.id", ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    # Adding the relationship to the role to access the associated role of a user using user.role
    role: Mapped["Role"] = relationship("Role", back_populates="users")   # from gpt

    # automatically creates a users attribute in the Role model to represent the reverse relationship
    # role: Mapped["Role"] = relationship("Role", backref="users")     # from course


class Chat(Base):
    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # If users send 'hi' messages, bot responds with default messages without getting response from OpenAI. Thus thread_id nullable.
    asst_thread_id: Mapped[str] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str] = mapped_column(String(15), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    user: Mapped["User"] = relationship("User", backref="chat")


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sender: Mapped[str] = mapped_column(String(15), nullable=False)
    bot_message_id: Mapped[str] = mapped_column(String(255), nullable=True)
    tg_message_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    # unique=True ensures one-to-one relationship
    reply_to_message_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("message.id", ondelete='CASCADE', onupdate='CASCADE'), nullable=True, unique=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat.id", ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    chat: Mapped["Chat"] = relationship("Chat", backref="message")

    # One-to-one relationship with the parent message (if it exists)
    # The backref="response_message" creates a reverse relationship, allowing access to all response/child messages from the parent message.
    # The uselist=False for the response_message ensures that each parent message can have only one child response.
    reply_to_message: Mapped["Message"] = relationship(
        "Message",
        # backref=backref("response_message", uselist=False),
        uselist=False
    )


class Reaction(Base):
    __tablename__ = "reaction"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    satisfied: Mapped[bool] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, nullable=True)
    message_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("message.id", ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    # One-to-one relationship from Reaction to Message
    message: Mapped["Message"] = relationship("Message", backref="reaction", uselist=False)


class File(Base):
    __tablename__ = "file"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asst_file_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    tg_file_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Numeric(), nullable=False)
    path: Mapped[str] = mapped_column(String(275), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    deleted_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete='CASCADE', onupdate='CASCADE'), nullable=True)

    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by])
    deleter: Mapped["User"] = relationship("User", foreign_keys=[deleted_by])