import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.setup_data import download
from backend.paths import DATA
# Three.js example assets. NASA imagery distributed with the three.js examples.
download('https://raw.githubusercontent.com/mrdoob/three.js/r160/examples/textures/planets/earth_atmos_2048.jpg',DATA/'assets/earth.jpg','NASA Earth imagery / three.js examples; present-day illustrative geography')
download('https://raw.githubusercontent.com/mrdoob/three.js/r160/examples/textures/planets/moon_1024.jpg',DATA/'assets/moon.jpg','NASA lunar imagery / three.js examples')
