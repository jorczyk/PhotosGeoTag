import PIL
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import folium
import glob
import base64
import uuid
import os

from branca.element import IFrame


class Position:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

    def __str__(self):
        return "lat: " + str(self.lat) + " lon: " + str(self.lon)


class GpsImageRef:

    def __init__(self, location, file, is_invalid=False):
        self.position = location
        self.path = file
        self.is_invalid = is_invalid
        # self.name = file

    def __str__(self):
        return "position:\n" + self.position.__str__()

    @classmethod
    def get_invalid(cls, file):
        return cls(None, file, True)


def get_exif(filename):
    try:
        print("trying to open file: " + str(filename))
        image = Image.open(filename)
        image.verify()
        return image._getexif()
    except:
        print("opening " + str(filename) + " failed")
        return None


def get_geotagging(exif):
    if not exif:
        return {}

    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == 'GPSInfo':
            if idx not in exif:
                return {}

            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]

    return geotagging


def dms_to_dd(d, m, s):
    dd = d + float(m) / 60 + float(s) / 3600
    return dd


def list_photos(directory):
    return glob.glob(directory + "/*.jpg")


def list_photos_recursively(root):
    return [f for f in glob.glob(root + "**/*.jpg", recursive=True)]


def create_images_gps_refs(photos):
    refs = []
    for image in photos:
        refs.append(create_image_gps_ref(image))
    return refs


def create_map_from_multiple(refs, name, include_ratio=1, with_images=False):
    map_object = folium.Map(location=[0, 0], zoom_start=4)
    counter = 0
    for img in refs:
        print(str(counter) + " out of " + str(len(refs)) + " done")
        if not img.is_invalid and counter % include_ratio == 0:
            map_object = place_single_poi(map_object, img, with_images=with_images)
            print(str(img.path) + " added to map")
        counter += 1
    folium.Map.save(map_object, "output/" + str(name) + ".html")


def place_single_poi(map_object, source, with_images=False):
    lon = source.position.lon
    lat = source.position.lat
    if with_images:
        [resized_image_path, height, width] = resize_image(source.path)
        encoded = base64.b64encode(open(resized_image_path, 'rb').read())
        html = '<img src="data:image/png;base64,{}">'.format
        iframe = IFrame(html(encoded.decode('UTF-8')), width=width + 30, height=height + 30)
        popup = folium.Popup(iframe, max_width=width + 30)
        marker = folium.features.Marker(location=[lat, lon], tooltip=str(source.path.split("\\")[-1]), popup=popup)
        os.remove(resized_image_path)
    else:
        marker = folium.features.Marker(location=[lat, lon])
    map_object.add_child(marker)
    return map_object


def resize_image(path):
    fixed_height = 400
    image = Image.open(path)
    height_percent = (fixed_height / float(image.size[1]))
    width_size = int((float(image.size[0]) * float(height_percent)))
    image = image.resize((width_size, fixed_height), PIL.Image.NEAREST)
    new_path = 'temp/' + str(uuid.uuid4()) + '.jpg'
    image.save(new_path)
    return [new_path, fixed_height, width_size]


def create_image_gps_ref(file):
    exif = get_exif(file)
    geotags = get_geotagging(exif)
    if geotags.get('GPSLatitude') is None or geotags.get('GPSLongitude') is None:
        ref = GpsImageRef.get_invalid(file)
    else:
        lat = dms_to_dd(float(geotags.get('GPSLatitude')[0]), float(geotags.get('GPSLatitude')[1]),
                        float(geotags.get('GPSLatitude')[2]))
        lon = dms_to_dd(float(geotags.get('GPSLongitude')[0]), float(geotags.get('GPSLongitude')[1]),
                        float(geotags.get('GPSLongitude')[2]))
        position = Position(lat, lon)
        ref = GpsImageRef(position, file)
    return ref


if __name__ == '__main__':
    directory = ""
    photos = list_photos(directory)
    # photos = list_photos_recursively(directory)
    refs = create_images_gps_refs(photos)
    create_map_from_multiple(refs, name=directory.split("\\")[-1], include_ratio=1)
    print("done!")
