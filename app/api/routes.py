from flask import jsonify, request
from app.api import bp
from app.models import Collection, Entry

@bp.route('/content/<collection_name>')
def get_content(collection_name):
    collection = Collection.query.filter_by(name=collection_name).first_or_404()
    
    entries = Entry.query.filter_by(
        collection_id=collection.id,
        status='published'
    ).all()
    
    if collection.is_singleton:
        entry = entries[0] if entries else None
        return jsonify(entry.to_dict() if entry else {})
    
    return jsonify([entry.to_dict() for entry in entries])

@bp.route('/content/<collection_name>/<slug>')
def get_entry(collection_name, slug):
    collection = Collection.query.filter_by(name=collection_name).first_or_404()
    
    entry = Entry.query.filter_by(
        collection_id=collection.id,
        slug=slug,
        status='published'
    ).first_or_404()
    
    return jsonify(entry.to_dict())

@bp.route('/collections')
def list_collections():
    collections = Collection.query.all()
    return jsonify([c.to_dict() for c in collections])