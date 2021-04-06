import argparse
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


def connect_to_drive(credential):
    """
    Creates new Google Drive connection
    :param credential: path to client_secret.json file
    :return: New Google Drive instance
    """
    gauth = GoogleAuth()
    scope = ['https://www.googleapis.com/auth/drive']
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(credential, scope)
    drive = GoogleDrive(gauth)
    return drive


def upload_file(file, folder, credential):
    """
    Uploads a file to a specified Google Drive folder.
    :param file: Source file to upload to drive
    :param folder: Name of Google Drive destination folder
    :param credential: Path to client_secret.json file
    :return: None
    """
    drive = connect_to_drive(credential=credential)
    folder_name = folder  # Please set the folder name.

    folders = drive.ListFile(
        {
            'q': "title='" + folder_name + "' ""and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for folder in folders:
        if folder['title'] == folder_name:
            file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
            for file1 in file_list:
                if file1['title'] == file:
                    file1.SetContentFile(file)
                    file1.Upload()
            else:
                file2 = drive.CreateFile({'parents': [{'id': folder['id']}]})
                file2.SetContentFile(file)
                file2.Upload()


def main():
    """
    Main method.
    :return: none
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--credential", help="path to Google API credential JSON file",
                        default="client_secret.json")
    parser.add_argument("-f", "--folder", help="name of google drive folder")
    parser.add_argument("-s", "--source", help="path to file for upload")
    args = parser.parse_args()
    credential = args.credential
    folder = args.folder
    source = args.source
    print("{0}: Uploading {1} to Google Drive folder: {2}".format(datetime.now(), source, folder))
    upload_file(source, folder, credential)



if __name__ == "__main__":
    main()
