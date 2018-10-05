# -*- coding: utf-8 -*-
import os
from subprocess import Popen, PIPE, call

from modules import cbpi, socketio
from modules.core.hardware import SensorActive
import json
from flask import Blueprint, render_template, jsonify, request
from modules.core.props import Property

blueprint = Blueprint('ispindel_alccalc', __name__)
cache = {}

def calcGravity(polynom, tilt, unitsGravity):
	if unitsGravity == "SG":
		rounddec = 3
	elif unitsGravity =="ALC":
		rounddec = 10
	else:
		rounddec = 2

	# Calculate gravity from polynomial
	tilt = float(tilt)
	result = eval(polynom)
	result = round(float(result),rounddec)
	return result
	
def calcAlcohol(gravity, origWort):
	realGravity = 0.1808*origWort + 0.8192*gravity
	result = (origWort-realGravity)/(2.0665-0.010665*origWort)*1.267
	result = round(float(result), 2)
	return result

@cbpi.sensor
class iSpindel_AlcCalc(SensorActive):
	key = Property.Text(label="iSpindel Name", configurable=True, description="Enter the name of your iSpindel")
	sensorType = Property.Select("Data Type", options=["Temperature", "Gravity", "Battery", "Alcohol Content"], description="Select which type of data to register for this sensor")
	tuningPolynom = Property.Text(label="Tuning Polynomial", configurable=True, default_value="tilt", description="Enter your iSpindel polynomial. Use the variable tilt for the angle reading from iSpindel. Does not support ^ character.")
	unitsGravity = Property.Select("Gravity Units", options=["SG", "Brix", "°P"], description="Displays gravity reading with this unit if the Data Type is set to Gravity. Does not convert between units, to do that modify your polynomial.")
	originalWort = Property.Text(label="Original Wort (°P)", configurable = True, description="Enter original wort in °P for alcohol percentage calculation")

	def get_unit(self):
		if self.sensorType == "Temperature":
			return "°C" if self.get_config_parameter("unit", "C") == "C" else "°F"
		elif self.sensorType == "Gravity":
			return self.unitsGravity
		elif self.sensorType == "Battery":
			return "V"
		elif self.sensorType == "Alcohol Content":
			return "Vol-%"
		else:
			return " "

	def stop(self):
		pass

	def execute(self):
		global cache
		while self.is_running():
			try:				
				if cache[self.key] is not None:
					if self.sensorType == "Gravity":
						reading = calcGravity(self.tuningPolynom, cache[self.key]['Angle'], self.unitsGravity)
					elif self.sensorType == "Alcohol Content":
					    reading = calcGravity(self.tuningPolynom, cache[self.key]['Angle'], "ALC")
					    reading = calcAlcohol(reading, float(self.originalWort))
					else:
						reading = cache[self.key][self.sensorType]
					self.data_received(reading)
			except:
				pass
			self.api.socketio.sleep(1) 

@blueprint.route('/api/hydrometer/v1/data', methods=['POST'])
def set_temp():
	global cache
	
	data = request.get_json()
	id = data["name"]
	temp = round(float(data["temperature"]), 2)
	angle = data["angle"]
	battery = data["battery"]

	cache[id] = {'Temperature': temp, 'Angle': angle, 'Battery': battery}

	return ('', 204)

@cbpi.initalizer()
def init(cbpi):
	print "INITIALIZE ISPINDEL ALCCALC MODULE"
	cbpi.app.register_blueprint(blueprint)
