# -*- coding: utf-8 -*-
import os
from subprocess import Popen, PIPE, call

from modules import cbpi, socketio
from modules.core.hardware import SensorActive
import json
from flask import Blueprint, render_template, jsonify, request
from modules.core.props import Property

blueprint = Blueprint('ispindel', __name__)
cache = {}

def calcGravity(polynom, tilt, unitsGravity):
	if unitsGravity == "SG":
		rounddec = 3
	else:
		rounddec = 2

	# Calculate gravity from polynomial
	tilt = float(tilt)
	result = eval(polynom)
	result = round(float(result),rounddec)
	return result

@cbpi.sensor
class iSpindel(SensorActive):
	key = Property.Text(label="iSpindel Name", configurable=True, description="Enter the name of your iSpindel")
	sensorType = Property.Select("Data Type", options=["Temperature", "Gravity", "Battery", "RSSI"], description="Select which type of data to register for this sensor")
	tuningPolynom = Property.Text(label="Tuning Polynomial", configurable=True, default_value="tilt", description="Enter your iSpindel polynomial. Use the variable tilt for the angle reading from iSpindel. Does not support ^ character.")
	unitsGravity = Property.Select("Gravity Units", options=["SG", "Brix", "°P"], description="Displays gravity reading with this unit if the Data Type is set to Gravity. Does not convert between units, to do that modify your polynomial.")
        stored_angle = 0

	def get_unit(self):
		if self.sensorType == "Temperature":
			return "°C" if self.get_config_parameter("unit", "C") == "C" else "°F"
		elif self.sensorType == "Gravity":
			return self.unitsGravity
		elif self.sensorType == "Battery":
			return "V"
                elif self.sensorType == "RSSI":
                        return "dBm"
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
                                                angle = cache[self.key]['Angle']
						reading = calcGravity(self.tuningPolynom, angle, self.unitsGravity)
                                                self.stored_angle = angle
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
        #iSpindel with old FW doesn't provide data about RSSI
        if 'RSSI' in data:
            rssi = data["RSSI"]
        else:
            rssi = 0
        cache[id] = {'Temperature': temp, 'Angle': angle, 'Battery': battery, 'RSSI' : rssi}

	return ('', 204)

@cbpi.initalizer()
def init(cbpi):
	print "INITIALIZE ISPINDEL MODULE"
	cbpi.app.register_blueprint(blueprint)
