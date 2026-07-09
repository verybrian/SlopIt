from flask import jsonify, request, url_for
from app.api import bp
from app.models import Collection, CollectionKind, Entry
from app.api.decorators import require_api_key


@bp.route('/content/<collection_name>')
@require_api_key
def get_content(collection_name):
    collection = Collection.query.filter_by(name=collection_name).first_or_404()
    
    if collection.kind == CollectionKind.SECTION:
        entry = Entry.query.filter_by(collection_id=collection.id).first()
        return jsonify(entry.to_dict() if entry else {})
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    
    pagination = Entry.query.filter_by(collection_id=collection.id)\
        .order_by(Entry.updated_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'data': [entry.to_dict() for entry in pagination.items],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_page': pagination.next_num if pagination.has_next else None,
            'prev_page': pagination.prev_num if pagination.has_prev else None,
        }
    })


@bp.route('/content/<collection_name>/<slug>')
@require_api_key
def get_entry(collection_name, slug):
    collection = Collection.query.filter_by(name=collection_name).first_or_404()
    
    entry = Entry.query.filter_by(
        collection_id=collection.id,
        slug=slug
    ).first_or_404()
    
    return jsonify(entry.to_dict())


@bp.route('/collections')
@require_api_key
def list_collections():
    collections = Collection.query.all()
    return jsonify([c.to_dict() for c in collections])