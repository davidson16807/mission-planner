from math import log, exp
from dataclasses import dataclass
from itertools import zip_longest

class Craft:
	def __init__(self,
		heatshield,
		lander,
		fuel_mass,
		max_fuel_mass,
		dry_mass,
		sealevel_thrust,
		sealevel_exhaust,
		vacuum_thrust,
		vacuum_exhaust,
		min_throttle,
		unpressurized_volume,
		pressurized_volume,
		habitable_volume,
	):
		self.heatshield = heatshield
		self.lander = lander
		self.fuel_mass = fuel_mass if fuel_mass is not None else 0
		self.max_fuel_mass = max_fuel_mass if max_fuel_mass is not None else 0
		self.dry_mass = dry_mass if dry_mass is not None else 0
		self.sealevel_thrust = sealevel_thrust if sealevel_thrust is not None else vacuum_thrust
		self.sealevel_exhaust = sealevel_exhaust if sealevel_exhaust is not None else vacuum_exhaust
		self.vacuum_thrust = vacuum_thrust if vacuum_thrust is not None else sealevel_thrust
		self.vacuum_exhaust = vacuum_exhaust if vacuum_exhaust is not None else sealevel_exhaust
		self.min_throttle = min_throttle if min_throttle is not None else 0.0
		self.unpressurized_volume = unpressurized_volume if unpressurized_volume is not None else 0.0
		self.pressurized_volume = pressurized_volume if pressurized_volume is not None else 0.0
		self.habitable_volume = habitable_volume if habitable_volume is not None else 0.0
		assert self.fuel_mass <= self.max_fuel_mass, f'invalid fuel mass: {self.fuel_mass} < {self.max_fuel_mass}'
		assert 0 <= self.fuel_mass, f'invalid fuel mass: 0 < {self.fuel_mass}'
	def copy(self):
		return Craft(
			self.heatshield, # delivery vehicle is presumed to protect its cargo
			self.lander,     # delivery vehicle is presumed to protect its cargo
			self.fuel_mass,
			self.max_fuel_mass,
			self.dry_mass,
			self.sealevel_thrust,
			self.sealevel_exhaust,
			self.vacuum_thrust,
			self.vacuum_exhaust,
			self.min_throttle,
			self.unpressurized_volume,
			self.pressurized_volume,
			self.habitable_volume,
		)
	def __repr__(self):
		return f'({self.dry_mass}🚀{self.fuel_mass}/{self.max_fuel_mass}\t→\t{self.sealevel_thrust}/{self.vacuum_thrust}\t{self.sealevel_exhaust}/{self.vacuum_exhaust})'
	def __add__(self, other):
		# return an craft where the left and right operands are flown together
		# example: sls = (2*srb5+slsme)>>orion
		return Craft(
			'',    # two capsules can't survive reentry strapped together
			False, # two boosters can't land strapped together
			self.fuel_mass + other.fuel_mass,
			self.max_fuel_mass + other.max_fuel_mass,
			self.dry_mass + other.dry_mass,
			self.sealevel_thrust + other.sealevel_thrust,
			other.sealevel_exhaust if self.sealevel_thrust == 0 else
			self.sealevel_exhaust if other.sealevel_thrust == 0 else
			(self.sealevel_thrust + other.sealevel_thrust) / 
				(self.sealevel_thrust/self.sealevel_exhaust + other.sealevel_thrust/other.sealevel_exhaust), 
				# weighted harmonic mean of exhausts, weighted by thrust
			self.vacuum_thrust + other.vacuum_thrust,
			other.vacuum_exhaust if self.vacuum_thrust == 0 else
			self.vacuum_exhaust if other.vacuum_thrust == 0 else
			(self.vacuum_thrust + other.vacuum_thrust) / 
				(self.vacuum_thrust/self.vacuum_exhaust + other.vacuum_thrust/other.vacuum_exhaust), 
				# weighted harmonic mean of exhausts, weighted by thrust
			(self.vacuum_thrust * self.min_throttle + other.vacuum_thrust * other.min_throttle) /
				(self.vacuum_thrust + other.vacuum_thrust),
				# weighted arithmetic mean of throttles, weighted by thrust
			self.unpressurized_volume + other.unpressurized_volume, 
			self.pressurized_volume + other.pressurized_volume,
			self.habitable_volume + other.habitable_volume, # may or may not require space walks
		)
	def __rmul__(self, other):
		# return an craft where the right operand is either scaled or flown in a fleet
		# example: sls = (2*srb5+slsme)>>orion
		return Craft(
			'',    # two capsules can't survive reentry strapped together
			False, # two boosters can't land strapped together
			other * self.fuel_mass,
			other * self.max_fuel_mass,
			other * self.dry_mass,
			other * self.sealevel_thrust,
			self.sealevel_exhaust,
			other * self.vacuum_thrust,
			self.vacuum_exhaust,
			self.min_throttle,
			other * self.unpressurized_volume, # don't know why you want to, but you can
			other * self.pressurized_volume,
			other * self.habitable_volume,
		)
	def __rshift__(self, other):
		# return an craft where the left operand pushes on the right operand as a payload
		# example: sls = (2*srb5+slsme)>>orion
		loaded = self.copy()
		loaded.dry_mass += other.total_mass()
		return loaded
	def exhaust(self, atmospheres):
		return (self.sealevel_exhaust-self.vacuum_exhaust) * atmospheres + self.vacuum_exhaust
	def thrust(self, atmospheres):
		return (self.sealevel_thrust-self.vacuum_thrust) * atmospheres + self.vacuum_thrust
	def range(self, atmospheres):
		return self.exhaust(atmospheres) * log(self.total_mass() / self.dry_mass)
	def max_range(self, atmospheres):
		return self.exhaust(atmospheres) * log(self.launch_mass() / self.dry_mass)
	def launch_mass(self):
		return self.dry_mass + self.max_fuel_mass
	def total_mass(self):
		return self.dry_mass + self.fuel_mass
	def with_fuel_mass(self, fuel_mass):
		copied = self.copy()
		copied.fuel_mass = fuel_mass
		assert copied.fuel_mass <= copied.max_fuel_mass, f'invalid fuel mass: {copied.fuel_mass} < {copied.max_fuel_mass}'
		assert 0 <= copied.fuel_mass, f'invalid fuel mass: 0 < {copied.fuel_mass}'
		return copied
	def empty(self):
		# returns the given craft in an empty state
		return self.with_fuel_mass(0.0)
	def fill(self):
		# returns the given craft in an full state
		return self.with_fuel_mass(self.max_fuel_mass)
	def burn(self, speed_change, atmospheres=0):
		# returns the state of a craft that starts a burn in a known state
		stop_mass = self.total_mass() / exp(speed_change / self.exhaust(atmospheres))
		assert stop_mass-self.dry_mass >= 0.0, f'fell short of fuel by {stop_mass-self.dry_mass} units'
		return self.with_fuel_mass(stop_mass-self.dry_mass)
	def deburn(self, speed_change, atmospheres=0):
		# returns the state of a craft that must reach a given state after a burn that causes a given change in speed
		mass_ratio = exp(speed_change / self.exhaust(atmospheres))
		start_mass = mass_ratio * self.total_mass()
		assert start_mass-self.dry_mass <= self.max_fuel_mass, f'over fuel capacity by {start_mass-self.dry_mass-self.max_fuel_mass} units, reduce dry mass by {self.dry_mass-self.launch_mass()/mass_ratio} units'
		return self.with_fuel_mass(start_mass - self.dry_mass)
	def boil(self, days, boiloff_rate=0.001): # default from Kutter (2008)
		# returns the state of a craft after boil off from waiting a given number of days with a given boil-off rate
		return self.with_fuel_mass(self.fuel_mass * (1.0-boiloff_rate)**days)
	def deboil(self, days, boiloff_rate=0.001): # default from Kutter (2008)
		# returns the state of a craft that must reach a given state after a boil off with a given boil-off rate
		return self.with_fuel_mass(self.fuel_mass / ((1.0-boiloff_rate)**days))

class CraftVectorCodec:
	def __init__(self):
		self.annotations = '_?ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡ'
	def encode(self, craft):
		return [str(entry) if entry is not None else ''
			for entry in [
				'','','','', # labels in csv
				craft.heatshield,
				'x' if craft.lander else '',
				craft.max_fuel_mass,
				craft.dry_mass,
				craft.sealevel_thrust,
				craft.sealevel_exhaust,
				craft.vacuum_thrust,
				craft.vacuum_exhaust,
				craft.min_throttle,
				craft.unpressurized_volume,
				craft.pressurized_volume,
				craft.habitable_volume,
			]]
	def decode(self, code):
		defaults = [None for i in range(5,14)]
		stripped = [entry.strip(self.annotations) for entry in code]
		floats = [(float(entry) if entry else default) 
			for entry,default in zip_longest(stripped[6:],defaults,fillvalue=None)]
		return Craft(
			stripped[4],
			stripped[5]=='x',
			floats[0], # fully fueled
			*floats
		)

class Properties:
	def __init__(self, 
			interplanetary_volume_per_person,
			earth_gravity):
		self.interplanetary_volume_per_person = interplanetary_volume_per_person
		self.earth_gravity = earth_gravity
	def sealevel_range(self, craft):
		return craft.sealevel_exhaust * log(craft.launch_mass() / craft.dry_mass)
	def vacuum_range(self, craft):
		return craft.vacuum_exhaust * log(craft.launch_mass() / craft.dry_mass)
	def launch_mass(self, craft):
		return craft.max_fuel_mass + craft.dry_mass
	def sealevel_fuel_consumption(self, craft):
		return craft.sealevel_thrust/craft.sealevel_exhaust
	def vacuum_fuel_consumption(self, craft):
		return craft.vacuum_thrust/craft.vacuum_exhaust
	def min_sealevel_acceleration(self, craft):
		return craft.sealevel_thrust / craft.launch_mass()
	def min_vacuum_acceleration(self, craft):
		return craft.vacuum_thrust / craft.launch_mass()
	def max_sealevel_acceleration(self, craft):
		return craft.sealevel_thrust / craft.dry_mass
	def max_vacuum_acceleration(self, craft):
		return craft.vacuum_thrust / craft.dry_mass
	def min_thrust_to_weight(self, craft): # answers "can it get off the ground?"
		return self.min_sealevel_acceleration(craft) / self.earth_gravity
	def max_nominal_g_force(self, craft): # answers "will g-forces kill you?"
		return self.max_vacuum_acceleration(craft) * craft.min_throttle / self.earth_gravity
	def max_off_nominal_g_force(self, craft): # answers "can g-forces kill you?"
		return self.max_vacuum_acceleration(craft) / self.earth_gravity
	def sealevel_power(self, craft): # really only useful for speculative electric vehicles
		return craft.sealevel_thrust * craft.sealevel_exhaust
	def vacuum_power(self, craft): # really only useful for speculative electric vehicles
		return craft.vacuum_thrust * craft.vacuum_exhaust
	def interplanetary_crew(self, craft):
		return craft.habitable_volume / self.interplanetary_volume_per_person

class DelimitedTableTextCodec:
	def __init__(self,
			row_delimiter='\n',
			column_delimiter='\t',
			header_count = 1,
		):
		self.row_delimiter = row_delimiter
		self.column_delimiter = column_delimiter
		self.header_count = header_count
	def encode(self, table):
		return self.row_delimiter.join([
			self.column_delimiter.join([cell for cell in row]) 
			for row in table
		])
	def decode(self, code):
		return [[cell.strip() for cell in row.split(self.column_delimiter)]
			for row in code.strip('\n ').split(self.row_delimiter)[self.header_count:] 
		]

class ListVectorCodec:
	def __init__(self, codec):
		self.codec = codec
	def encode(self, content):
		return [self.codec.encode(entry) for entry in content]
	def decode(self, code):
		return [self.codec.decode(entry) for entry in code]

class LookupVectorCodec:
	def __init__(self, codec, key_id):
		self.codec = codec
		self.key_id = key_id
	def encode(self, content):
		return [[key, *self.codec.encode(entry)] for key, entry in content] # TODO: use key_id here
	def decode(self, code):
		return {entry[self.key_id]: self.codec.decode(entry) for entry in code}

class CodecComposition:
	def __init__(self, encoder1, encoder2):
		self.encoder1 = encoder1
		self.encoder2 = encoder2
	def encode(self, content):
		return self.encoder2.encode(self.encoder1.encode(content))
	def decode(self, code):
		return self.encoder1.decode(self.encoder2.decode(code))

if __name__ == '__main__':

	properties = Properties(
		25,   # m³/person
		0.98, # Dm/s² (makes reasoning with units easier, thrust must be reported in DkN)
	)

	tsvs = CodecComposition(
			LookupVectorCodec(CraftVectorCodec(), 3),
			DelimitedTableTextCodec())

	with open('rss-crafts.tsv','r') as file:
		df = tsvs.decode(file.read())

	'''
	PLACE ABBREVIATIONS:
	earth 	earth ground
	leo 	lower earth orbit
	eeo 	eccentric earth orbit
	heo 	high earth orbit
	elt 	earth to lunar transfer

	met 	mars to earth transfer
	lmo 	lower martian orbit
	emo 	eccentric martian orbit
	hmo 	high martian orbit
	emt 	earth-mars transfer
	mars 	mars ground

	lvo 	lower veneran orbit
	evo 	eccentric veneran orbit
	hvo 	high veneran orbit
	vet 	earth to venus transfer
	evt 	venus to earth transfer

	CRAFT ABBREVIATIONS:
	hlso 	starship human landing system with orion: mli, no heatshield, no fins, no legs, docked to orion with european space module
	ssc 	crewed starship: heatshield, fins, legs, no mli
	ssd 	starship depot: mli, no heatshield, no fins, no legs, habitable volume converted to fuel tanks
	'''

	ssc_terminal_velocity_over_earth = 0.33 # observed from starship flight 11

	# times assume a typicaly 850 day Hohmann-transfer mars mission
	time_at_mars_entry = 270 # days
	time_at_met = 700 # days
	time_on_mars = time_at_met - time_at_mars_entry
	ss_terminal_velocity_over_mars = ss_terminal_velocity_over_earth * 4.8

	# times are spit balls assuming 400 day mission as suggested by 1970s Apollo applications study
	time_at_venus_entry = 130 # days
	time_at_vet = 260 # days
	time_over_venus = time_at_vet - time_at_venus_entry

	# LUNAR HLS STARSHIP:
	hls_leo = (df['sslc4'] + 23*df['Mg']).empty().deburn(2*(2.44+0.68+0.14+0.68+1.72)) 

	# CREWED VENUS FLYBY USING HLS/ORION:
	# hls+orion payload, mass budget for a crew of 4 on the ISS
	hlso_empty = ((df['sso3'] + 90*df['Mg']) >> df['orion']).empty()
	# hls+orion at evo before earth departure
	hlso_evo = hlso_empty.deburn(0.36)
	# hls+orion at vet after earth departure
	hlso_vet = hlso_evo.deboil(time_at_vet)
	# hls+orion over venus before insertion
	hlso_evo = hlso_empty.deburn(0.36)
	# hls+orion at vet after earth departure
	hlso_vet = hlso_evo.deboil(time_at_venus_entry)
	# hls+orion at leo before earth departure
	hlso_leo = hlso_vet.deburn(2.44+0.68+0.09+0.28+0.36)

	# CREWED MARS FLYBY USING HLS/ORION:
	# hls+orion payload, mass budget for a crew of 4 on the ISS
	hlso_empty = ((df['sso3'] + 90*df['Mg']) >> df['orion']).empty()
	# hls+orion at emo before earth departure
	hlso_emo = hlso_empty.deburn(0.67)
	# hls+orion at emt after earth departure
	hlso_emt = hlso_emo.deboil(time_at_met)
	# hls+orion at leo before earth departure
	hlso_leo = hlso_emt.deburn(2.44+0.68+0.09+0.39+0.67)

	# STARSHIP INTERSTELLAR PROBE VELOCITY:
	print((df['ssf3'] >> df['vger']).range(0))

	# STARSHIP URANUS ORBITER VELOCITY:
	(df['ssf3'] >> df['cassini']).empty().deburn(2.44+0.68+0.09+0.39+0.92+0.38+1.40+0.99+0.69)

	# CREWED MARS LANDING ASSUMING fuel DEPOT AT LMO:
	# starship crew payload, mass budget for a crew of 4 on the ISS for 850 days
	ssc_empty = (df['ssc4'] + 90*df['Mg']).empty()
	# starship crew at lmo before crew return to earth
	ssc_lmo = ssc_empty.deburn(0.33+2.11)
	# starship depot at lmo before crew return for earth
	ssd_lmo = df['ssd4'].with_fuel_mass(ssc_lmo.fuel_mass)
	# starship depot at leo before burn to mars
	ssd_leo = (ssd_lmo.deboil(time_at_met).deburn(5.71))
	# starship crew at mars before return launch
	ssc_mars = ssc_empty.deburn(3.6)
	# starship crew at emt after earth departure
	ssc_emt = ssc_mars.deboil(time_on_mars).deburn(ss_terminal_velocity_over_mars).deboil(time_at_met)
	# starship crew when refueled at eeo before earth departure
	ssc_eeo = ssc_emt.deburn(3.52-2.44-0.68)

	breakpoint()

	# much of what follows will raise errors due to fuel limits:

	# CREWED MARS LANDING ASSUMING FUEL TANKER ON MARS:
	# this doesn't work - the tanker needs to burn more for the landing, stores less fuel, and carries heatshield/legs/fins
	# starship crew payload, mass budget for a crew of 4 on the ISS for 850 days
	ssc_empty = (df['ssc4'] + 90*df['Mg']).empty()
	# starship crew at mars before return launch
	ssc_mars = ssc_empty.deburn(0.33+2.11+3.6)
	# starship depot on mars before crew return for earth
	sst_lmo = df['sst4'].with_fuel_mass(ssc_mars.fuel_mass)
	# starship depot at leo before burn to mars
	sst_leo = (sst_lmo.deboil(time_at_met).deburn(5.71+0.33*4.8))
	# starship crew at emt after earth departure
	ssc_emt = ssc_mars.deboil(time_on_mars).deburn(ss_terminal_velocity_over_mars).deboil(time_at_met) # can't do it, error
	# starship crew when refueled at elt before earth departure
	ssc_elt = ssc_emt.deburn(3.52-2.44-0.68)

	# ASSUMING NO ISRU NOR fuel DEPOT:
	ssc_direct = ssc_lmo.deburn(3.6).deboil(time_at_met).deburn(3.52) # can't do it, error
