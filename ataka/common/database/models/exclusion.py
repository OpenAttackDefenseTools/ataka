from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from ..config import Base, JsonBase


class Exclusion(Base, JsonBase):
    __tablename__ = "exclusions"

    exploit_history_id = Column(String, ForeignKey("exploit_histories.id"),
                                primary_key=True)
    target_ip = Column(String, primary_key=True)

    exploit_history = relationship("ExploitHistory", back_populates="exclusions")
