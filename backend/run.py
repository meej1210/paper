from app import create_app


app = create_app()


if __name__ == "__main__":
    # The Flask reloader watches the project tree and would restart the API
    # when uploaded scan targets or generated reports change on disk.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
