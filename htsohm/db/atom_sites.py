from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from htsohm.db import Base

class AtomSite(Base):
    __tablename__ = "atom_sites"

    id = Column(Integer, primary_key=True)
    atom_type = Column(String(10))
    lennard_jones_id = Column(Integer, ForeignKey("lennard_jones.id"))

    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    q = Column(Float)

    structure_id = Column(Integer, ForeignKey("structures.id"))
    lennard_jones = relationship("LennardJones")

    def exclude_cols(self):
        return ['id']

    def clone(self):
        copy = super(AtomSite, self).clone()
        return copy

    def __repr__(self):
        return "(%s: %s, %f, %f, %f, %f)" % (str(self.id), self.atom_type, self.x, self.y, self.z, self.q)
