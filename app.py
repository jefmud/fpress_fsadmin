# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, abort, g, session

from flask_simple_admin import Admin
import os
import sys

app = Flask(__name__)
app.secret_key = 'yourSecretHere'
admin = Admin(app)

def featured_pages():
    """returns a list of featured pages"""
    pages = app.db.pages.find({'is_featured': 'on'})
    return pages

@app.before_request
def before_request():
    # default values
    g.stylesheet = ''
    g.logo = '/static/images/fp_logo_alt_100x100.png'
    g.brand = 'FlaskPress'
    g.menu = []
    pages = app.db.pages.find({})
    g.menu = [ page for page in pages if page.get('include_in_nav', False) ]
    g.site = app.db.site.find_one({})
    if session.get('username'):
        g.username = session['username']
    if session.get('is_authenticated'):
        g.is_authenticated = session['is_authenticated']
    if g.site.get('stylesheet'):
        g.stylesheet = g.site.get('stylesheet')
    if g.site.get('brand'):
        g.brand = g.site.get('brand')
    if session.get('logo'):
        g.logo = g.site.get('logo')

@app.route('/')
@app.route('/<path:slug>')
def page_view(slug='home'):
    """renders a page"""
    page = app.db.pages.find_one({'slug': slug})
    if page:
        # get sidebar and footer pages, if any
        sidebar_right = app.db.pages.find_one({'slug': page.get('sidebar_right_slug', '')})
        sidebar_left = app.db.pages.find_one({'slug': page.get('sidebar_left_slug', '')})
        footer = app.db.pages.find_one({'slug': page.get('footer_slug', '')})
        
        # get theme
        theme = g.site.get('theme', 'default')
        # check if the template exists
        if not os.path.exists(f'templates/themes/{theme}/page.html'):
                theme = 'default'
        # render the page
        return render_template(
            f'themes/{theme}/page.html',
            page=page,
            sidebar_left=sidebar_left, sidebar_right=sidebar_right, footer=footer,
            featured_pages=featured_pages()
            )
    else:
        return abort(404)

@app.route('/<path:slug>/edit')
def page_edit(slug):
    """admin (only) page for editing a page"""
    # get page
    page = app.db.pages.find_one({'slug': slug})
    if page is None:
        # check if user is authenticated (can create new pages)
        if g.get('is_authenticated', False):
            page = {'slug': slug}
            app.db.pages.insert_one(page)
        else:
            return abort(404)
    # redirects to admin_edit_schema (feature of flask_simple_admin)
    next = url_for('page_view', slug=slug)
    return redirect(url_for('admin_edit_schema', coll='pages', id=str(page['_id']), next=next))

def get_search_results(s):
    """returns a list of pages matching the search string"""
    # get all pages
    allpages = app.db.pages.find({})
    # filter pages
    pages = [
     page for page in allpages if page.get('is_published') == "on" and (
      s in page.get('title', '').lower() or s in page.get('content', '').lower())
    ]
    return pages

@app.route('/search')
def search():
    """searches for pages, returns a list of pages matching the search string"""
    search_term = request.args.get('s', '').lower()
    pages = get_search_results(search_term)
    
    # get theme
    theme = g.site.get('theme', 'default')
    
    # check if the template exists, otherwise use 'default'
    if not os.path.exists(f'templates/themes/{theme}/page.html'):
        theme = 'default'
        
    return render_template(f'themes/{theme}/search.html', pages=pages, s=search_term)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        admin.user_services_cli(sys.argv)
    else:
        admin.user_services_cli(['--host', '0.0.0.0', '--runserver', '--server', 'twisted'])
