from flask import Response, json, send_file, request
from flask_restful import Resource
from __init__ import conn
import requests
import io
from marshmallow import Schema, fields, validate, ValidationError, validates

class RequestPathParamsSchema(Schema):
    id = fields.Str(required=True, description='Property ID')

class GeometrySchema(Schema):
    type = fields.Str(validate = validate.OneOf(["Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"]), required = True)
    coordinates = fields.List(fields.Float(), required = True)
    
class ExpectedJSONSchema(Schema):
    location = fields.Nested(GeometrySchema, required = True)
    distance = fields.Float(required = True)

    @validates("distance")
    def validate_quantity(self, value):
        if value < 0:
            raise ValidationError("Quantity must be greater than 0.")
        if value > 10000000:
            raise ValidationError("Quantity must not be greater than 10000000.")

class StatsQueryParamsSchema(Schema):
    zone_size_m = fields.Integer(required=True)

    @validates("zone_size_m")
    def validate_quantity(self, value):
        if value < 0:
            raise ValidationError("Quantity must be greater than 0.")

class IdValidator():
    def CheckId(self, id):
        cur = conn.cursor()
        cur.execute(f"SELECT EXISTS(SELECT 1 FROM properties WHERE id='{id}')")
        exists = True if cur.fetchone()[0] == 1 else False
        return exists

class DisplayApi(Resource, IdValidator):
    def get(self, id):
        if not self.CheckId(id):
                return {"error": "id do not exist in database"}, 400
        cur = conn.cursor()
        cur.execute(f"SELECT image_url FROM properties WHERE id = '{id}'")
        image_url = cur.fetchone()
        if image_url == None:
            return Response(json.dumps({"errors": "image not found"}), mimetype="application/json", status=404)
        else:
            response = requests.get(image_url[0])
            return send_file(io.BytesIO(response.content), mimetype='image/jpeg', as_attachment=True, attachment_filename=f'{id}.jpg')

class FindaApi(Resource):
    def post(self):
        data = request.get_json()
        try:
            result = ExpectedJSONSchema().load(data)
            distance = result['distance']
            coordinates = result['location']['coordinates']
            cur = conn.cursor()
            cur.execute(f"SELECT geom.id, round(CAST(ST_Distance(geom.geocode_geo, ST_GeogFromText('POINT(-80.0782200 26.8849700)')) As numeric),2) As dist_meters FROM (SELECT id, geocode_geo FROM properties WHERE ST_DWithin(geocode_geo,ST_GeogFromText('POINT({coordinates[0]} {coordinates[1]})'), {distance}, false)) AS geom ORDER BY dist_meters ASC")
            properties = cur.fetchall()
            keys = ['property_id', 'distance_m']
            data = [dict(zip(keys, prop)) for prop in properties]
            return Response(json.dumps(data), mimetype="application/json", status=200)
        except ValidationError as err:
            return {"errors": err.messages}, 400

class StatsApi(Resource, IdValidator):
    def get(self, id):
        try:
            qry_args = StatsQueryParamsSchema().load(request.args)
            path = RequestPathParamsSchema().load(request.view_args)
            id_property = path['id']
            zone_size_m = qry_args['zone_size_m']

            if not self.CheckId(id):
                return {"error": "id do not exist in database"}, 400

            # Get parcel area
            cur = conn.cursor()
            cur.execute(f"SELECT ST_Area(parcel_geo) as parcel_area FROM properties WHERE id = '{id_property}'")
            parcel_area = cur.fetchone()[0]

            # Get building area
            cur = conn.cursor()
            cur.execute(f"SELECT ST_Area(building_geo) as building_area FROM properties WHERE id = '{id_property}'")
            building_area = cur.fetchone()[0]

            # Get building distance
            cur = conn.cursor()
            cur.execute(f"SELECT ST_Distance(calc.geocode_geo, calc.building_centroid) AS Building_distance FROM (SELECT ST_Centroid(building_geo) AS building_centroid, geocode_geo FROM properties WHERE id = '{id_property}') AS calc")
            building_distance = cur.fetchone()[0]

            # Get zone density
            cur = conn.cursor()
            cur.execute(f"SELECT ST_Area(ST_Intersection(calc.zone_geo, calc.building_geo))/ST_Area(calc.zone_geo) AS percentage FROM (SELECT ST_Buffer(geocode_geo, 10) as zone_geo, building_geo from properties where id = '{id_property}') as calc")
            zone_density = cur.fetchone()[0]

            return Response(json.dumps({"parcel_area_sqm": parcel_area, "building_area_sqm": building_area, "building_distance_m": building_distance, "zone_density": zone_density}), mimetype="application/json", status=200)
        except ValidationError as err:
            return {"errors": err.messages}, 400

