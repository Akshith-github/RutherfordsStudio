from flask import render_template, request, jsonify
from . import main


@main.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('error_msg.html',error_name="404",error_desc="Page not found",extra="please report the issue.",
    link="mailto:rutherfordsstudio@gmail.com" , link_txt = "Admin mail : rutherfordsstudio@gmail.com"), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('error_msg.html',error_name="500",error_desc="Internal Server error",extra="Send a feedback mail to Admin mail",link="mailto:rutherfordsstudio@gmail.com" , link_txt = "Admin mail : rutherfordsstudio@gmail.com"
    ), 500

@main.app_errorhandler(403)
def forbidden(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('error_msg.html',error_name="403",error_desc="Forbidden Error",extra="contact to site admin", link="mailto:rutherfordsstudio@gmail.com" , link_txt = "Admin mail : rutherfordsstudio@gmail.com"
    ), 403
    # return render_template('403.html'), 403