from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from htsohm.db import Base

class LennardJones(Base):
    __tablename__ = "lennard_jones"

    id = Column(Integer, primary_key=True)
    atom_type = Column(String(10))
    sigma = Column(Float)
    epsilon = Column(Float)

    # relationship with 'structures'
    structure_id = Column(Integer, ForeignKey("structure.id"))

    def __init__(self, atom_type=None, sigma=None, epsilon=None):
        self.atom_type = atom_type
        self.sigma = sigma
        self.epsilon = epsilon

    def exclude_cols(self):
        return ['id']

    def clone(self):
        copy = super(LennardJones, self).clone()
        return copy

    def __repr__(self):
        return "(%s: %s, sigma: %f, epsilon: %f)" % (str(self.id), self.atom_type, self.sigma, self.epsilon)
