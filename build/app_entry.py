import os
import sys
import warnings
from streamlit.web import cli as stcli
import streamlit.config as _config

from backend.path_resolver import resource_path
warnings.filterwarnings("ignore")


def main():
    app_path = resource_path(os.path.join("ui", "app.py"))

    # disable dev mode so port/address work
    # _config.set_option("global.developmentMode", False)
    # os.environ["STREAMLIT_DEVELOPMENT_MODE"] = "false" # force disable dev mode via enviornment variable

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.address=10.166.194.83", #server address : 10.166.194.83
        "--server.port=8083",
        "--global.developmentMode=false",
        "--server.baseUrlPath=LTS_CHATBOT",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
