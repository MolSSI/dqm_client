import numpy as np

import dqm_client as dqm
from dqm_client import molecule

from . import test_helper as th

_water_dimer_minima_np = np.array([[8, -1.551007, -0.114520, 0.000000], [1, -1.934259, 0.762503, 0.000000],
                                   [1, -0.599677, 0.040712, 0.000000], [8, 1.350625, 0.111469, 0.000000],
                                   [1, 1.680398, -0.373741, -0.758561], [1, 1.680398, -0.373741, 0.758561]])

_neon_tetramer_np = np.array([[10, 0.000000, 0.000000, 0.000000], [10, 3.100000, 0.000000, 0.000000],
                              [10, 0.000000, 3.200000, 0.000000], [10, 0.000000, 0.000000, 3.300000]])
_neon_tetramer_np[:, 1:] *= dqm.constants.physconst["bohr2angstroms"]


def test_molecule_constructors():

    ### Water Dimer
    water_psi = dqm.data.get_molecule("water_dimer_minima.psimol")
    water_from_np = molecule.Molecule(_water_dimer_minima_np, name="water dimer", dtype="numpy", frags=[3])

    assert water_psi.compare(water_psi, water_from_np)

    # Check the JSON construct/deconstruct
    water_from_json = molecule.Molecule(water_psi.to_json(), dtype="json")
    assert water_psi.compare(water_psi, water_from_json)

    ### Neon Tetramer
    neon_from_psi = dqm.data.get_molecule("neon_tetramer.psimol")
    neon_from_np = molecule.Molecule(_neon_tetramer_np, name="neon tetramer", dtype="numpy", frags=[1, 2, 3])

    assert water_psi.compare(neon_from_psi, neon_from_np)

    # Check the JSON construct/deconstruct
    neon_from_json = molecule.Molecule(neon_from_psi.to_json(), dtype="json")
    assert water_psi.compare(neon_from_psi, neon_from_json)


def test_water_minima_data():
    mol = dqm.data.get_molecule("water_dimer_minima.psimol")
    mol.name = "water dimer"

    assert len(str(mol)) == 662
    assert len(mol.to_string()) == 442

    assert sum(x == y for x, y in zip(mol.symbols, ['O', 'H', 'H', 'O', 'H', 'H'])) == mol.geometry.shape[0]
    assert np.allclose(mol.masses,
                       [15.99491461956, 1.00782503207, 1.00782503207, 15.99491461956, 1.00782503207, 1.00782503207])
    assert mol.name == "water dimer"
    assert mol.charge == 0
    assert mol.multiplicity == 1
    assert np.sum(mol.real) == mol.geometry.shape[0]
    assert np.allclose(mol.fragments, [[0, 1, 2], [3, 4, 5]])
    assert np.allclose(mol.fragment_charges, [0, 0])
    assert np.allclose(mol.fragment_multiplicities, [1, 1])
    assert hasattr(mol, "provenance")
    assert np.allclose(mol.geometry, [[2.81211080, 0.1255717, 0.], [3.48216664, -1.55439981, 0.],
                                      [1.00578203, -0.1092573, 0.], [-2.6821528, -0.12325075, 0.],
                                      [-3.27523824, 0.81341093, 1.43347255], [-3.27523824, 0.81341093, -1.43347255]])
    assert mol.get_hash() == "476ae9e1023d6e4aed7b01b36a3a9e8b5651d0f6"


def test_water_minima_fragment():

    mol = dqm.data.get_molecule("water_dimer_minima.psimol")

    frag_0 = mol.get_fragment(0)
    frag_1 = mol.get_fragment(1)
    assert frag_0.get_hash() == "b7852644b6f6909c7748c5b53b45a782497715d9"
    assert frag_1.get_hash() == "55dcb95d08fa42c80035fcf3ee4926778a60a549"

    frag_0_1 = mol.get_fragment(0, 1)
    frag_1_0 = mol.get_fragment(1, 0)

    assert mol.symbols[:3] == frag_0.symbols
    assert np.allclose(mol.masses[:3], frag_0.masses)

    assert mol.symbols == frag_0_1.symbols
    assert np.allclose(mol.geometry, frag_0_1.geometry)

    assert mol.symbols[3:] + mol.symbols[:3] == frag_1_0.symbols
    assert np.allclose(mol.masses[3:] + mol.masses[:3], frag_1_0.masses)


def test_water_orient():
    # These are identical molecules, should find the correct results

    mol = dqm.data.get_molecule("water_dimer_stretch.psimol")
    frag_0 = mol.get_fragment(0)
    frag_1 = mol.get_fragment(1)

    # Make sure the fragments match
    assert frag_0.get_hash() == frag_1.get_hash()

    # Make sure the complexes match
    frag_0_1 = mol.get_fragment(0, 1)
    frag_1_0 = mol.get_fragment(1, 0)

    assert frag_0_1.get_hash() == frag_1_0.get_hash()

    mol = dqm.data.get_molecule("water_dimer_stretch2.psimol")
    frag_0 = mol.get_fragment(0)
    frag_1 = mol.get_fragment(1)

    # Make sure the fragments match
    assert frag_0.get_hash() == frag_1.get_hash()

    # Make sure the complexes match
    frag_0_1 = mol.get_fragment(0, 1)
    frag_1_0 = mol.get_fragment(1, 0)

    # Ghost fragments should prevent overlap
    assert frag_0_1.get_hash() != frag_1_0.get_hash()
