"""
DQM Molecule object and helpers
"""

import numpy as np
import itertools as it
import re
import os
import math
import hashlib
import json

from . import constants
from . import fields
from . import schema
from . import hash_helpers

# Rounding quantities for hashing
GEOMETRY_NOISE = 8
MASS_NOISE = 6
CHARGE_NOISE = 4


class Molecule:
    """
    This is a Mongo QCDB molecule class.
    """

    def __init__(self, mol_str, **kwargs):
        """
        the Mongo QCDB molecule class which is capable of reading and writing many formats.
        """

        # Layout all known attributes
        self.symbols = []
        self.geometry = None

        self.masses = []
        self.name = kwargs.pop("name", "")
        self.comment = ""
        self.charge = 0.0
        self.multiplicity = 1
        self.real = []
        self.fragments = []
        self.fragment_charges = []
        self.fragment_multiplicities = []
        self.provenance = {}

        # List any flags
        self._custom_masses = False
        self._fix_com = True
        self._fix_orientation = True

        # Figure out how and if we will parse the Molecule adata
        dtype = kwargs.pop("dtype", "psi4").lower()
        if mol_str is not None:
            if dtype == "psi4":
                self._molecule_from_string_psi4(mol_str)
            elif dtype == "numpy":
                frags = kwargs.pop("frags", [])
                self._molecule_from_numpy(mol_str, frags, units=kwargs.pop("units", "angstrom"))
            elif dtype == "json":
                self._molecule_from_json(mol_str)
            else:
                raise KeyError("Molecule: dtype of %s not recognized.")

            if kwargs.pop("orient", True):
                self.orient_molecule()
        else:
            # In case a user wants to build one themselves
            pass

        if len(kwargs):
            raise KeyError("Not all kwargs were correctly parsed, remaining: %s" % ", ".join(kwargs.keys()))



    @classmethod
    def from_file(cls, filename, dtype=None, orient=True):
        """
        Constructs a molecule object from a file.
        """

        ext = os.path.splitext(filename)[1]

        if dtype is not None:
            if ext in ["psimol"]:
                dtype = "psi4"
            elif ext in ["npy"]:
                dtype = "numpy"
            elif ext in ["json"]:
                dtype = "json"
            else:
                raise KeyError("No dtype provided and ext '%s' not understood." % ext)
        else:
            dtype = "psi4"

        if dtype == "psi4":
            with open(filename, "r") as infile:
                data = infile.read()
        elif dtype == "numpy":
            data = numpy.fromfile(filename)
        elif dtype == "json":
            with open(filename, "r") as infile:
                data = json.loads(infile)
        else:
            raise KeyError("Dtype not understood '%s'." % dtype)

        return cls(data, dtype=dtype, orient=orient)

    def _molecule_from_json(self, json_data):
        """
        From a given valid JSON molecule spec, rebuild the class.
        """

        for field, data in json_data.items():
            if field == "geometry":
                setattr(self, field, np.array(data, dtype=np.double))
            else:
                setattr(self, field, data)

    def _molecule_from_numpy(self, arr, frags, units="angstrom"):
        """
        Given a NumPy array of shape (N, 4) where each row is (Z_nuclear, X, Y, Z).

        Frags represents the splitting pattern for molecular fragments. Geometry must be in
        Angstroms.
        """

        arr = np.array(arr)

        if arr.shape[1] != 4:
            raise AttributeError("Molecule: Molecule should be shape (N, 4) not %d." % arr.shape[1])

        if units == "bohr":
            const = 1
        elif units == "angstrom":
            const = 1 / constants.physconst["bohr2angstroms"]
        else:
            raise KeyError("Unit '%s' not understood" % units)

        self.geometry = arr[:, 1:].copy() * const
        self.real = [True for x in arr[:, 0]]

        if len(frags) and (frags[-1] != arr.shape[0]):
            frags.append(arr.shape[0])

        start = 0
        for fsplit in frags:
            self.fragments.append(list(range(start, fsplit)))
            self.fragment_charges.append(0.0)
            self.fragment_multiplicities.append(1)
            start = fsplit

    def _molecule_from_string_psi4(self, text):
        """Given a string *text* of psi4-style geometry specification
        (including newlines to separate lines), builds a new molecule.
        Called from constructor.

        """

        # Setup re expressions
        comment = re.compile(r'^\s*#')
        blank = re.compile(r'^\s*$')
        bohr = re.compile(r'^\s*units?[\s=]+(bohr|au|a.u.)\s*$', re.IGNORECASE)
        ang = re.compile(r'^\s*units?[\s=]+(ang|angstrom)\s*$', re.IGNORECASE)
        atom = re.compile(
            r'^(?:(?P<gh1>@)|(?P<gh2>Gh\())?(?P<label>(?P<symbol>[A-Z]{1,3})(?:(_\w+)|(\d+))?)(?(gh2)\))(?:@(?P<mass>\d+\.\d+))?$',
            re.IGNORECASE)
        cgmp = re.compile(r'^\s*(-?\d+)\s+(\d+)\s*$')
        frag = re.compile(r'^\s*--\s*$')
        ghost = re.compile(r'@(.*)|Gh\((.*)\)', re.IGNORECASE)
        realNumber = re.compile(r"""[-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?""", re.VERBOSE)

        lines = re.split('\n', text)
        glines = []
        ifrag = 0

        # Assume angstrom, we want bohr
        unit_conversion = 1 / constants.physconst["bohr2angstroms"]

        for line in lines:

            # handle comments
            if comment.match(line) or blank.match(line):
                pass

            # handle units
            elif bohr.match(line):
                unit_conversion = 1.0

            elif ang.match(line):
                pass

            # handle charge and multiplicity
            elif cgmp.match(line):
                tempCharge = int(cgmp.match(line).group(1))
                tempMultiplicity = int(cgmp.match(line).group(2))

                if ifrag == 0:
                    self.charge = float(tempCharge)
                    self.multiplicity = tempMultiplicity
                self.fragment_charges.append(float(tempCharge))
                self.fragment_multiplicities.append(tempMultiplicity)

            # handle fragment markers and default fragment cgmp
            elif frag.match(line):
                try:
                    self.fragment_charges[ifrag]
                except:
                    self.fragment_charges.append(0.0)
                    self.fragment_multiplicities.append(1)
                ifrag += 1
                glines.append(line)

            elif atom.match(line.split()[0].strip()):
                glines.append(line)
            else:
                raise TypeError(
                    'Molecule:create_molecule_from_string: Unidentifiable line in geometry specification: %s' % (line))

        # catch last default fragment cgmp
        try:
            self.fragment_charges[ifrag]
        except:
            self.fragment_charges.append(0.0)
            self.fragment_multiplicities.append(1)

        # Now go through the rest of the lines looking for fragment markers
        ifrag = 0
        iatom = 0
        tempfrag = []
        atomSym = ""
        atomLabel = ""
        self.geometry = []
        tmpMass = []

        # handle number values

        for line in glines:

            # handle fragment markers
            if frag.match(line):
                ifrag += 1
                self.fragments.append(list(range(tempfrag[0], tempfrag[-1] + 1)))
                self.real.extend([True for x in range(tempfrag[0], tempfrag[-1] + 1)])
                tempfrag = []

            # handle atom markers
            else:
                entries = re.split(r'\s+|\s*,\s*', line.strip())
                atomm = atom.match(line.split()[0].strip().upper())
                atomLabel = atomm.group('label')
                atomSym = atomm.group('symbol')

                # We don't know whether the @C or Gh(C) notation matched. Do a quick check.
                ghostAtom = False if (atomm.group('gh1') is None and atomm.group('gh2') is None) else True

                # Check that the atom symbol is valid
                if not atomSym in constants.el2z:
                    raise TypeError(
                        'Molecule:create_molecule_from_string: Illegal atom symbol in geometry specification: %s' %
                        (atomSym))

                self.symbols.append(atomSym)
                zVal = constants.el2z[atomSym]
                if atomm.group('mass') is None:
                    atomMass = constants.el2masses[atomSym]
                else:
                    atomMass = float(atomm.group('mass'))
                    self._custom_masses = True
                tmpMass.append(atomMass)

                charge = float(zVal)
                if ghostAtom:
                    zVal = 0
                    charge = 0.0

                # handle cartesians
                if len(entries) == 4:
                    tempfrag.append(iatom)
                    if realNumber.match(entries[1]):
                        xval = float(entries[1])
                    else:
                        raise TypeError("Molecule::create_molecule_from_string: Unidentifiable entry %s.", entries[1])

                    if realNumber.match(entries[2]):
                        yval = float(entries[2])
                    else:
                        raise TypeError("Molecule::create_molecule_from_string: Unidentifiable entry %s.", entries[2])

                    if realNumber.match(entries[3]):
                        zval = float(entries[3])
                    else:
                        raise TypeError("Molecule::create_molecule_from_string: Unidentifiable entry %s.", entries[3])

                    self.geometry.append([xval, yval, zval])
                else:
                    raise TypeError('Molecule::create_molecule_from_string: Illegal geometry specification line : %s. \
                        You should provide either Z-Matrix or Cartesian input' % (line))

                iatom += 1

        if self._custom_masses:
            self.masses = tmpMass

        self.geometry = np.array(self.geometry) * unit_conversion
        self.fragments.append(list(range(tempfrag[0], tempfrag[-1] + 1)))
        self.real.extend([True for x in range(tempfrag[0], tempfrag[-1] + 1)])

    def compare(self, other, bench=None):
        """
        Checks if two molecules are identical
        """

        if bench is None:
            bench = self

        match = True
        match &= bench.symbols == other.symbols
        if self._custom_masses or other._custom_masses:
            match &= np.allclose(bench.masses, other.masses, atol=MASS_NOISE)
        match &= np.equal(bench.real, other.real).all()
        match &= np.equal(bench.fragments, other.fragments).all()
        match &= np.allclose(bench.fragment_charges, other.fragment_charges, atol=CHARGE_NOISE)
        match &= np.equal(bench.fragment_multiplicities, other.fragment_multiplicities).all()

        match &= np.allclose(bench.charge, other.charge, atol=CHARGE_NOISE)
        match &= np.equal(bench.multiplicity, other.multiplicity).all()
        match &= np.allclose(bench.geometry, other.geometry, atol=GEOMETRY_NOISE)
        return match

    def pretty_print(self):
        """Print the molecule in Angstroms. Same as :py:func:`print_out` only always in Angstroms.
        (method name in libmints is print_in_angstrom)

        """
        text = ""

        text += """    Geometry (in %s), charge = %.1f, multiplicity = %d:\n\n""" % \
            ('Angstrom', self.charge, self.multiplicity)
        text += """       Center              X                  Y                   Z       \n"""
        text += """    ------------   -----------------  -----------------  -----------------\n"""

        for i in range(len(self.geometry)):
            text += """    %8s%4s """ % (self.symbols[i], "" if self.real[i] else "(Gh)")
            for j in range(3):
                text += """  %17.12f""" % (self.geometry[i][j] * constants.physconst["bohr2angstroms"])
            text += "\n"
        text += "\n"

        return text

    def __repr__(self):
        return self.pretty_print()

    def _inertial_tensor(self, geom, weight):
        """
        Compute the moment inertia tensor for a given geometry.
        """
        # Build inertia tensor
        tensor = np.zeros((3, 3))

        # Diagonal
        tensor[0][0] = np.sum(weight * (geom[:, 1]**2.0 + geom[:, 2]**2.0))
        tensor[1][1] = np.sum(weight * (geom[:, 0]**2.0 + geom[:, 2]**2.0))
        tensor[2][2] = np.sum(weight * (geom[:, 0]**2.0 + geom[:, 1]**2.0))

        # I(alpha, beta)
        # Off diagonal
        tensor[0][1] = -1.0 * np.sum(weight * geom[:, 0] * geom[:, 1])
        tensor[0][2] = -1.0 * np.sum(weight * geom[:, 0] * geom[:, 2])
        tensor[1][2] = -1.0 * np.sum(weight * geom[:, 1] * geom[:, 2])

        # Other half
        tensor[1][0] = tensor[0][1]
        tensor[2][0] = tensor[0][2]
        tensor[2][1] = tensor[1][2]
        return tensor

    def orient_molecule(self):
        """
        Centers the molecule and orients via inertia tensor.
        """

        # Get the mass as an array

        # Masses are needed for orientation
        if self._custom_masses is False:
            np_mass = np.array([constants.el2masses[x] for x in self.symbols])
        else:
            np_mass = np.array(self.masses)

        # Center on Mass
        self.geometry -= np.average(self.geometry, axis=0, weights=np_mass)

        # Rotate into inertial frame
        tensor = self._inertial_tensor(self.geometry, np_mass)
        evals, evecs = np.linalg.eigh(tensor)

        self.geometry = np.dot(self.geometry, evecs)

        # Phases? Fuck it, lets do the simplest thing and ensure the first atom in each column
        # that is not on a plane is positve

        phase_check = [False, False, False]

        geom_noise = 10**(-GEOMETRY_NOISE)
        for num in range(self.geometry.shape[0]):

            for x in range(3):
                if phase_check[x]: continue

                val = self.geometry[num, x]

                if (abs(val) < geom_noise): continue

                phase_check[x] = True

                if (val < 0):
                    self.geometry[:, x] *= -1

            if sum(phase_check) == 3:
                break

    def get_fragment(self, real, ghost=None, orient=True):
        """
        A list of real and ghost fragments:
        """

        if isinstance(real, int):
            real = [real]

        if isinstance(ghost, int):
            ghost = [ghost]
        elif ghost is None:
            ghost = []

        # ret_name = self.name + " (" + str(real) + "," + str(ghost) + ")"
        ret_name = self.name
        ret = Molecule(None, name=ret_name)

        if len(set(real) & set(ghost)):
            raise TypeError("Molecule:get_fragment: real and ghost sets are overlaping! (%s, %s)." % (str(real),
                                                                                                      str(ghost)))

        geom_blocks = []

        # Loop through the real blocks
        frag_start = 0
        for frag in real:
            frag_size = len(self.fragments[frag])
            geom_blocks.append(self.geometry[self.fragments[frag]])

            for idx in self.fragments[frag]:
                ret.symbols.append(self.symbols[idx])
                ret.masses.append(self.masses[idx])
                ret.real.append(True)

            ret.fragments.append(list(range(frag_start, frag_start + frag_size)))
            frag_start += frag_size

            ret.fragment_charges.append(float(self.fragment_charges[frag]))
            ret.fragment_multiplicities.append(self.fragment_multiplicities[frag])

        # Set charge and multiplicity
        ret.charge = sum(ret.fragment_charges)
        ret.multiplicity = sum(x - 1 for x in ret.fragment_multiplicities)

        # Loop through the ghost blocks
        for frag in ghost:
            frag_size = len(self.fragments[frag])
            geom_blocks.append(self.geometry[self.fragments[frag]])

            for idx in self.fragments[frag]:
                ret.symbols.append(self.symbols[idx])
                ret.masses.append(self.masses[idx])
                ret.real.append(False)

            ret.fragments.append(list(range(frag_start, frag_start + frag_size)))
            frag_start += frag_size

            ret.fragment_charges.append(self.fragment_charges[frag])
            ret.fragment_multiplicities.append(self.fragment_multiplicities[frag])

        ret.geometry = np.vstack(geom_blocks)

        if orient:
            ret.orient_molecule()

        return ret

    def to_string(self, dtype="psi4"):
        """Returns a string that can be used by a variety of programs.
        """
        if dtype == "psi4":
            return self._to_psi4_string()
        else:
            raise KeyError("Molecule:to_string: dtype of '%s' not recognized." % dtype)

    def _to_psi4_string(self):
        """Regenerates a input file molecule specification string from the
        current state of the Molecule. Contains geometry info,
        fragmentation, charges and multiplicities, and any frame
        restriction.
        """
        text = "\n"

        # append atoms and coordentries and fragment separators with charge and multiplicity
        for num, frag in enumerate(self.fragments):
            divider = "    --"
            if num == 0:
                divider = ""

            if any(self.real[at] for at in frag):
                text += "%s    \n    %d %d\n" % (divider, self.fragment_charges[num],
                                                 self.fragment_multiplicities[num])

            for at in frag:
                if self.real[at]:
                    text += "    %-8s" % self.symbols[at]
                else:
                    text += "    %-8s" % ("Gh(" + self.symbols[at] + ")")
                text += "    % 14.10f % 14.10f % 14.10f\n" % tuple(self.geometry[at])
        text += "\n"

        # append units and any other non-default molecule keywords
        text += "    units bohr\n"
        text += "    no_com\n"
        text += "    no_reorient\n"

        return text

    def to_json(self):
        """
        Returns a JSON form of the Molecule object.
        """

        np.set_printoptions(precision=16)
        ret = {}
        for field in fields.valid_fields["molecule"]:
            data = getattr(self, field)

            # Do we add this data?
            if isinstance(data, (np.ndarray, list, tuple)) and (len(data) == 0): continue

            # If we added masses for orientation, continue
            if (field == "masses") and (self._custom_masses is False):
                continue

            if field == "geometry":
                ret[field] = hash_helpers.float_prep(data, GEOMETRY_NOISE).tolist()
            elif field == "fragment_charges":
                ret[field] = hash_helpers.float_prep(data, CHARGE_NOISE).tolist()
            elif field == "charge":
                ret[field] = hash_helpers.float_prep(data, CHARGE_NOISE)
            elif field == "masses":
                ret[field] = hash_helpers.float_prep(data, MASS_NOISE).tolist()
            else:
                ret[field] = data

        return ret

    def get_hash(self):
        """
        Returns the hash of the molecule.
        """

        m = hashlib.sha1()
        concat = ""

        tmp_json = self.to_json()
        for field in schema.get_hash_fields("molecule"):
            if field not in tmp_json:
                continue
            concat += json.dumps(tmp_json[field])

        m.update(concat.encode("utf-8"))
        return m.hexdigest()
