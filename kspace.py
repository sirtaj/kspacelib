#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:        kspace
# Purpose:     Reads Kerbal Space Program parts and ships.
#
# Author:      Sirtaj Singh Kang
#
# Created:     24/03/2012
# Copyright:   (c) Sirtaj Singh Kang 2012
# Licence:     LGPL
#-------------------------------------------------------------------------------

__doc__=\
'''
    Reads ships and parts from an installed copy of Kerbal Space Program.

    Once the ships and parts are loaded, there are convenience functions to allow various analyses 
    to be performed on the ships.

    Basic usage:

        import kspace
        kspace.set_game_path("C:\\games\\KSP_win")
        kspace.Part.load_all()
        ships = kspace.Ship.load_all()

        ship = ships[0]
        print "Ship name:", ship.name, "with", len(ship.stages), "stages."
        launch_stage = ship.stages[-1]
        mass_at_launch = launch_stage.mass()
        print "thrusters at launch:", launch_stage.available_thrusters()
'''

import os.path as op
import dircache, pprint

GAME_PATH="C:\\games\\KSP_win"
PART_DEF_SUBPATH = "Parts"
SHIPS_SUBPATH = 'Ships'
PART_DEFS = {} # part_id -> Part

def set_game_path(path):
    global GAME_PATH
    GAME_PATH = path


##### Attribute readers for basic types ####

def read_generic(obj, key, val):
    '''Generic attribute setter.
    Checks for a specific setter (named "read_<attr>"), otherwise sets to string value (read_skip).
    '''
    setter = getattr(obj, 'read_' + key, None)
    if setter: setter(key, val)
    else: read_skip(obj, key, val)

def read_string(obj, key, value): setattr(obj, key, value)
def read_int(obj, key, value): setattr(obj, key, int(value))
def read_float(obj, key, value): setattr(obj, key, float(value))
def read_string_list(obj, key, value): setattr(obj, key, value.split(','))
def read_bool(obj, key, value):setattr(obj, key, value.lower() in ['true', '1'])
def read_float_list(obj, key, value):
    setattr(obj, key, tuple(float(v.strip()) for v in value.split(',')))
def read_int_list(obj, key, value):
    setattr(obj, key, tuple(int(v.strip()) for v in value.split(',')))

read_ident = read_string
read_point = read_float_list
read_vector = read_float_list
read_time = read_float
read_mass = read_float
read_stage = read_int
read_temp = read_float
read_force = read_float

SKIPPED_KEYS = {} # maintains a list of keys that we didn't read for debugging

def read_skip(obj, key, value):
    setattr(obj, key, value)
    SKIPPED_KEYS.setdefault(key, []).append((obj, value))

###############################


class Part(object):
    #__metaclass__ = PartLibrary

    def __init__(self):
        self.name = ''
        self.fuelCrossFeed = False
        self.node_stack = {}

    def __repr__(self):
        return "<%s %s: %s>" % (self.__class__.__name__, self.module, self.name)

    ##### Factory #####

    @classmethod
    def get_module_class(klazz, module_name):
        subcls = globals()[module_name]
        obj = subcls()
        obj.module = module_name
        return obj

    ##### Instance methods #####

    def is_engine(self): return False

    #### Attributes #####

    # general params
    read_name = read_ident
    read_author = read_string

    # node defs
    read_node_attach = read_float_list

    # asset
    read_mesh = read_string
    read_scale = read_float
    read_texture = read_string
    read_specPower = read_float
    read_rimFalloff = read_float
    read_alphaCutoff = read_float

    # editor parameters
    read_cost = read_float
    read_category = read_int
    read_subcategory = read_int
    read_title = read_string
    read_manufacturer = read_string
    read_description = read_string
    read_iconCenter = read_point
    read_icon = read_string
    read_iconScale = read_vector

    read_attachRules = read_int_list

    # standard part parameters
    read_mass = read_mass
    read_dragModelType = read_string
    read_maximum_drag = read_force
    read_minimum_drag = read_force
    read_angularDrag = read_float
    read_crashTolerance = read_float
    read_maxTemp = read_temp
    read_breakingForce = read_force
    read_breakingTorque = read_float
    read_stageBefore = read_bool
    read_stageAfter = read_bool
    read_fuelCrossFeed = read_bool

    # generic
    def read_attribute(self, key, value):
        if key.startswith('node_stack_'):
            key = key.replace('node_stack_', '')
            self.node_stack[key] = \
                    tuple(float(v.strip()) for v in value.split(','))
        elif key.startswith('fx_') or key.startswith('sound_'):
            # skip sounds and fx
            return
        else:
            read_generic(self, key, value)

    #### READ #######

    @staticmethod
    def load_all(parts_dir = None):
        if parts_dir is None:
            parts_dir = op.join(GAME_PATH, PART_DEF_SUBPATH)

        for part_subdir in dircache.listdir(parts_dir):
            print "Reading part:", part_subdir
            part_cfg_path = op.join(parts_dir, part_subdir, "part.cfg")
            part_def = Part.load(part_cfg_path)
            PART_DEFS[part_def.name] = part_def

        return PART_DEFS

    @staticmethod
    def load(part_path):
        pf = open(part_path)

        values = {}
        for ln in pf.readlines():
            ln = ln.strip()
            if ln.startswith('//'): continue
            if '=' not in ln: continue

            key, val = [v.strip() for v in ln.split('=', 1)]
            values[key] = val
            #part.read_attribute(key, val)

        module = values.pop('module')
        part = Part.get_module_class(module)
        for k,v in values.iteritems():
            part.read_attribute(k, v)

        return part


#####################

class Explosive:
    read_explosionPotential = read_float
    read_fullExplosionPotential = read_float
    read_emptyExplosionPotential = read_float

class SASBase(Part):
    read_torque = read_float
    read_maxTorque = read_float
    read_Ki = read_float
    read_Kd = read_float
    read_Kp = read_float

class CommandPod(SASBase):
    read_linPower = read_float
    read_rotPower = read_float

class AdvSASModule(SASBase): pass
class SASModule(SASBase): pass

class FuelBase(Part, Explosive):
    read_fuel = read_float
    read_dryMass = read_mass

class FuelTank(FuelBase): pass

class Parachutes(Part):
    read_useAGL = read_bool
    read_autoDeployDelay = read_float
    read_minAirPressureToOpen = read_float
    read_deployAltitude = read_float
    read_closedDrag = read_float
    read_semiDeployedDrag = read_float
    read_fullyDeployedDrag = read_float
    read_stageOffset = read_stage

class DecouplerBase(Part):
    read_ejectionForce = read_force
    read_childStageOffset = read_stage
    read_stageOffset = read_stage

class Decoupler(DecouplerBase): pass
class RCSFuelTank(FuelBase): pass

class RCSModule(Part):
    read_thrustVector0 = read_vector
    read_thrustVector1 = read_vector
    read_thrustVector2 = read_vector
    read_thrustVector3 = read_vector
    read_fuelConsumption = read_float

class EngineBase(Part):
    read_heatProduction = read_float
    read_fuelConsumption = read_float
    read_thrustVectoringCapable = read_bool
    read_gimbalRange = read_float

    def is_engine(self): return True

class SolidRocket(EngineBase, Explosive):
    read_thrust = read_float
    read_dryMass = read_mass
    read_internalFuel = read_float

    read_thrustCenter = read_point
    read_thrustVector = read_vector

class LiquidEngine(EngineBase):
    read_maxThrust = read_float
    read_minThrust = read_float

class LandingLeg(Part):
    read_extensionTime = read_time
    read_retractTime = read_time
    read_pivotAxis = read_point
    read_pivotingAngle = read_float

class ConnectorBase(Part, Explosive):
    read_linearStrength = read_float
    read_angularStrength = read_float
    read_maxLength = read_float

class StrutConnector(ConnectorBase): pass
class FuelLine(ConnectorBase): pass

class Strut(DecouplerBase):
    '''This is an odd one, since the RadialDecoupler is declared as a strut in the standard parts library.
    '''
    read_stackSymmetry = read_int

class RadialDecoupler(Strut): pass

class ControlledDragBase(Part, Explosive):
    read_dragCoeff = read_float
    read_deflectionLiftCoeff = read_float

class Winglet(ControlledDragBase): pass

class ControlSurface(ControlledDragBase):
    read_ctrlSurfaceRange = read_float
    read_ctrlSurfaceArea = read_float

######################


class Ship:
    def __init__(self, part_library):
        self.ship = ''
        self.part_library = part_library
        self.parts = []
        self.part = {} # part index by name
        self.stages = []

    read_ship = read_string
    read_version = read_string
    read_attribute = read_generic

    def resolve_links(self):
        istg = {}
        dstg = {}
        sqor = {}
        for p in self.parts:
            p.resolve_links()
            istg.setdefault(p.istg, []).append(p)
            dstg.setdefault(p.dstg, []).append(p)
            sqor.setdefault(p.sqor, []).append(p)

        stage_count = max(max(istg.keys()), max(dstg.keys())) + 1
        self.stages = [Stage(self, s, ignition = istg.get(s),
                                    detach = dstg.get(s))
                        for s in xrange(stage_count)]

    def __repr__(self):
        return "<Ship %s>" % (self.ship,)

    @staticmethod
    def load(ship_file, part_library = PART_DEFS):
        shipf = open(ship_file, 'r')
        ship = Ship(part_library = part_library)
        part = ship
        for ln in shipf.readlines():
            ln = ln.strip()
            if ln == '' or ln.startswith('//'):
                continue
            elif ln.startswith('}'):
                part = ship
                continue
            elif ln.startswith('{'):
                part = RealizedPart(ship)
                continue
            key, val = [v.strip() for v in ln.split('=', 1)]
            part.read_attribute(key, val)

        ship.resolve_links()
        return ship

    @staticmethod
    def load_all(ships_dir = None, part_library = PART_DEFS):
        if ships_dir is None:
            ships_dir = op.join(GAME_PATH, SHIPS_SUBPATH)

        ships = []
        for ship_dir in dircache.listdir(ships_dir):
            ship = Ship.load(op.join(ships_dir, ship_dir), part_library)
            ships.append(ship)
        return ships


class RealizedPart(object):
    '''A realized part belonging to a ship'''

    def __init__(self, ship):
        self.part_type = None
        self.part_id = None

        self.ship = ship
        ship.parts.append(self)
        self.links = []
        self.attachments = {} # (pos, part)
        self.surface_attachments = []
        self.sym = []

    def __repr__(self):
        if self.part_type:
            ptype = self.part_type.name
        else:
            ptype = "Part"

        return '<%s: %s>' % (ptype, self.part_id)

    def resolve_links(self):
        pid = self.ship.part
        self.links = [pid[l] for l in self.links]
        self.surface_attachments = [pid[l] for l in self.surface_attachments]
        self.sym = [pid[l] for l in self.sym]
        for locn, part in self.attachments.items():
            self.attachments[locn] = pid[part]

    def read_part(self, key, value):
        part_type, part_id = value.split('_', 1)
        self.part_type = self.ship.part_library[part_type]
        self.part_id = value
        setattr(self, key, value)
        self.ship.part[value] = self

    def read_sym(self, key, value):
        self.sym.append(value)

    def read_attN(self, key, value):
        locn, part_id = value.split(',')
        self.attachments[locn.strip()] = part_id.strip()

    def read_srfN(self, key, value):
        locn, part_id = value.split(',')
        self.surface_attachments.append(part_id.strip())

    def read_link(self, key, value):
        self.links.append(value.strip())

    def read_cData(self, key, value):
        '''Fuel line links'''
        subattrs = value.split(';')

    read_pos = read_point
    read_rot = read_vector
    read_istg = read_stage
    read_dstg = read_stage
    read_sidx = read_stage
    read_sqor = read_stage
    read_attm = read_int

    read_attribute = read_generic


class Stage:
    def __init__(self, ship, stage_num,
                ignition = None, detach = None, sqor = None):
        self.ship = ship
        self.stage_num = stage_num
        self.ignition = ignition or []
        self.detach = detach or []
        self.sqor = sqor or []

    def mass(self):
        mass_so_far = 0
        for stage in self.ship.stages:
            if stage.stage_num > self.stage_num:
                break
            for p in stage.ignition:
                mass_so_far += p.part_type.mass

        return mass_so_far

    def available_thrusters(self):
        ignited = {}
        detached = {}
        for stage in self.ship.stages[self.stage_num:]:
            ignited.update((p, 1) for p in stage.ignition if p.part_type.is_engine())
            detached.update((p, 1) for p in stage.detach if p.part_type.is_engine())

        return [i for i in ignited.iterkeys() if i not in detached]


def print_ships():
    import pprint
    Part.load_all()
    if SKIPPED_KEYS:
        print "skipped:"
        pprint.pprint(SKIPPED_KEYS)

    ships = Ship.load_all()
    if SKIPPED_KEYS:
        print "skipped:"
        pprint.pprint(SKIPPED_KEYS)

    ship = ships[0]
    print "ship", ship, "stages:", len(ship.stages)
    eng = [(th.istg, th.dstg, th.sqor, th)
                for th in ship.part.values()
                    if th.part_type.is_engine()]
    eng.sort()
    print "engines:", len(eng)
    pprint.pprint(eng)

    for s in ship.stages:
        print '-------------------'
        print "stage:", s.stage_num, "mass:", s.mass()
        print "detach:", sorted(s.detach)
        print "ignite:", sorted(s.ignition)
        print "thrusters:", sorted(s.available_thrusters())


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        set_game_path(sys.argv[1])
    print_ships()
