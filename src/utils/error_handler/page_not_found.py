from flask import render_template


def return_404_page(e):
    "Custom html page with message"
    return render_template("404.html"), 404
