from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
import os
import hashlib

from ingester.neo4j_ingester import MCIngester
from reconstructor.mc_reconstructor import MCReconstructor
from urllib.parse import urlparse

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USER")
NEO4J_PWD = os.getenv("NEO4J_PWD")

mc_ingester = MCIngester(NEO4J_URI, NEO4J_USERNAME, NEO4J_PWD)
mc_reconstructor = MCReconstructor(NEO4J_URI, NEO4J_USERNAME, NEO4J_PWD)

app = Flask(__name__)
api = Api(app, version='1.0', title='Patra API',
          description='API to interact with Patra Knowledge Graph',
          doc='/swagger')


@app.route('/')
def home():
    return "Welcome to the Patra Knowledge Base", 200

@api.route('/upload_mc')
class UploadModelCard(Resource):
    def post(self):
        """
        Upload model card to the Patra Knowledge Graph.
        Expects a JSON payload.
        """
        data = request.get_json()
        exists, base_mc_id = mc_ingester.add_mc(data)
        if exists:
            return {"message": "Model card already exists", "model_card_id": base_mc_id}, 200
        return {"message": "Successfully uploaded the model card", "model_card_id": base_mc_id}, 200

@api.route('/update_mc')
class UpdateModelCard(Resource):
    def post(self):
        """
        Update the existing model card.
        Expects a JSON payload.
        """
        data = request.get_json()
        base_mc_id = mc_ingester.update_mc(data)
        if base_mc_id:
            return {"message": "Successfully updated the model card", "model_card_id": base_mc_id}, 200
        return {"message": "Model card not found", "model_card_id": base_mc_id}, 200


@api.route('/upload_ds')
class UploadDatasheet(Resource):
    def post(self):
        """
        Upload datasheet to the Patra Knowledge Graph.
        Expects a JSON payload.
        """
        datasheet_data = request.get_json()
        mc_ingester.add_datasheet(datasheet_data)
        return {"message": "Successfully uploaded the datasheet"}, 200


@api.route('/search')
class SearchKG(Resource):
    @api.param('q', 'The search query')
    def get(self):
        """
        Full text search for model cards.
        """
        query = request.args.get('q')
        if not query:
            return {"error": "Query (q) is required"}, 400

        results = mc_reconstructor.search_kg(query)
        return results, 200


@api.route('/download_mc')
class DownloadModelCard(Resource):
    @api.param('id', 'The model card ID')
    def get(self):
        """
        Download a reconstructed model card from the Patra Knowledge Graph.
        """
        mc_id = request.args.get('id')
        if not mc_id:
            return {"error": "ID is required"}, 400

        model_card = mc_reconstructor.reconstruct(str(mc_id))

        if model_card is None:
            return {"error": "Model card could not be found!"}, 400

        return model_card, 200

@api.route('/download_url')
class ModelDownloadURL(Resource):
    @api.param('model_id', 'The model ID')
    def get(self):
        """
        Download url for a given model id.
        """
        model_id = request.args.get('model_id')
        if not model_id:
            return {"error": "Model ID is required"}, 400

        # get the model information
        model = mc_reconstructor.get_model_location(str(model_id))

        if model is None:
            return {"error": "Model could not be found!"}, 400

        return model, 200


@api.route('/list')
class ListModels(Resource):
    def get(self):
        """
        Lists all the models in Patra KG.
        """
        model_card_dict = mc_reconstructor.get_all_mcs()
        return model_card_dict, 200

# Get deployment information
@api.route('/model_deployments')
class DeploymentInfo(Resource):
    @api.param('model_id', 'The model ID')
    def get(self):
        """
        Get all deployments for a given model ID.
        """
        model_id = request.args.get('model_id')
        if not model_id:
            return {"error": "Model ID is required"}, 400

        deployments = mc_reconstructor.get_deployments(model_id)

        if deployments is None:
            return {"error": "Deployments not found!"}, 400

        return jsonify(deployments), 200

# Update model location
@api.route('/update_model_location')
class UpdateModelLocation(Resource):
    def post(self):
        """
        Update the model location.
        Expects a JSON payload.
        """
        data = request.get_json()
        if data is None:
            return {"error": "Invalid JSON payload"}, 400
        model_id = data.get('model_id')
        location = data.get('location')

        if not model_id or not location:
            return {"error": "Model ID and Location are required"}, 400

        parsed_url = urlparse(location)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            return {"error": "Location must be a valid URL"}, 400

        mc_reconstructor.set_model_location(model_id, location)
        return {"message": "Model location updated successfully"}, 200

@api.route('/get_hash_id')
class GenerateHashId(Resource):
    @api.param('combined_string', 'The combined string to be hashed')
    def get(self):
        """
        Return a unique hash for the provided combined_string.
        """
        combined_string = request.args.get('combined_string')

        # Validate input parameters
        if not combined_string:
            return {"error": " combined string is required"}, 400

        id_hash = mc_ingester.get_hash_id(combined_string)
        if id_hash is None:
            return {"error": "Hash ID has not been generated"}, 400
        return id_hash, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)