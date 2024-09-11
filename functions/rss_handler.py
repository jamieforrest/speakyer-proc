import boto3  # type: ignore
import logging
from datetime import datetime
from s3_utils import write_text_to_s3
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

s3 = boto3.client("s3")
logger = logging.getLogger()


def format_date_rss(date: datetime) -> str:
    return date.strftime("%a, %d %b %Y %H:%M:%S +0000")


def handle_rss(bucket_name: str):
    """Generate an RSS feed from the audio files in the S3 bucket.

    Parameters:
        bucket_name (str): The name of the S3 bucket to generate the RSS feed from
    """
    base_url = f"https://{bucket_name}.s3.amazonaws.com/"
    audio_files_prefix = "audios/"

    # Fetch the list of audio files from S3
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=audio_files_prefix)

    # Start building the RSS XML structure
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    # Add basic channel info
    title = SubElement(channel, "title")
    title.text = "Jamie Forrest's Speakyer Podcast"

    link = SubElement(channel, "link")
    link.text = "https://speakyer.com"

    description = SubElement(channel, "description")
    description.text = "Turn anything into a podcast."

    # Add the podcast items (episodes) for each audio file

    for obj in response.get("Contents", []):
        if obj["Key"].endswith(".mp3"):  # Adjust for your audio format
            item = SubElement(channel, "item")

            item_title = SubElement(item, "title")
            item_title.text = (
                obj["Key"].replace(audio_files_prefix, "").replace(".mp3", "")
            )

            item_link = SubElement(item, "link")
            item_link.text = base_url + obj["Key"]

            item_guid = SubElement(item, "guid")
            item_guid.text = base_url + obj["Key"]

            item_pubDate = SubElement(item, "pubDate")
            last_modified = obj["LastModified"]
            item_pubDate.text = format_date_rss(last_modified)

            _ = SubElement(
                item,
                "enclosure",
                url=base_url + obj["Key"],
                length=str(obj["Size"]),
                type="audio/mpeg",
            )

    # Convert the ElementTree to a string and format it
    rss_string = tostring(rss, encoding="utf-8")
    dom = parseString(rss_string)
    pretty_rss = dom.toprettyxml(indent="  ")

    write_text_to_s3(bucket_name, "rss/podcast_feed.xml", pretty_rss)

    logger.info(f"RSS feed generated successfully!: {pretty_rss}")
