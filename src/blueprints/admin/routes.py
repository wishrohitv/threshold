from flask import Blueprints, render_template


admin = Blueprints("admin", __name__, template_folder="templates")


@admin.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    return render_template("dashboard.html")
