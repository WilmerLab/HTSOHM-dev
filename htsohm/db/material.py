import uuid

from sqlalchemy import ForeignKey, Column, Integer, String, Float
from sqlalchemy.orm import relationship

from htsohm.db import Base, GasLoading, SurfaceArea, VoidFraction
from htsohm.db.structure import Structure

class Material(Base):
    """Declarative class mapping to table storing material/simulation data.

    Attributes:
        id (int): database table primary_key.
        run_id (str): identification string for run.
    """
    __tablename__ = 'materials'

    id           = Column(Integer, primary_key=True)
    run_id       = Column(String(50))
    uuid         = Column(String(40))
    parent_id    = Column(Integer, ForeignKey('materials.id'))

    # structure properties
    unit_cell_volume     = Column(Float)
    number_density       = Column(Float)
    average_epsilon      = Column(Float)
    average_sigma        = Column(Float)

    # relationships
    gas_loading       = relationship("GasLoading")
    surface_area      = relationship("SurfaceArea")
    void_fraction     = relationship("VoidFraction")
    structure         = relationship("Structure", uselist=False, back_populates="material")
    parent            = relationship("Material", remote_side=[id])

    def __init__(self, run_id, parent=None):
        """Init material-row.

        Args:
            self (class): row in material table.
            run_id : identification string for run (default = None).

        Initializes row in materials datatable.

        """
        self.uuid = str(uuid.uuid4())
        if parent:
            self.parent = parent
            self.parent_id = parent.id
        self.run_id = run_id
        self.structure = Structure()

    def clone(self):
        copy = super(Material, self).clone()
        return copy

    def __repr__(self):
        return "(%s: %s-%s p: %s)" % (self.run_id, str(self.id), self.uuid, self.parent_id)
