import os

from .helper import name_from_path
from azure.storage.blob import BlobServiceClient


def blob_name_from_file_page(file_path, files_directory, page=0):
    file_name = name_from_path(file_path, files_directory=files_directory)

    if file_name.split(".")[1] == "pdf":
        return file_name.split(".")[0] + f"-{page}" + ".pdf"
    else:
        return os.path.basename(file_name)


def upload_blobs_docs(
    file_path, files_directory, storageaccount, storage_creds, containerdocs
):
    blob_service = BlobServiceClient(
        account_url=f"https://{storageaccount}.blob.core.windows.net",
        credential=storage_creds,
    )
    blob_container = blob_service.get_container_client(containerdocs)
    if not blob_container.exists():
        blob_container.create_container()

    file_name = name_from_path(file_path, files_directory=files_directory)
    print(f"filename: {file_name}")

    with open(file_path, "rb") as data:
        blob_container.upload_blob(file_name, data, overwrite=True)


def remove_blobs_docs(
    file_path,
    files_directory,
    containerdocs,
    storageaccount,
    storage_creds,
    isPath=True,
    verbose=False,
):
    if verbose:
        print(f"Removing blobs (from container {containerdocs}) for '{file_path}'")
    blob_service = BlobServiceClient(
        account_url=f"https://{storageaccount}.blob.core.windows.net",
        credential=storage_creds,
    )
    blob_container = blob_service.get_container_client(containerdocs)
    if blob_container.exists():
        try:
            if isPath:
                blob_container.delete_blob(
                    name_from_path(file_path=file_path, files_directory=files_directory)
                )
            else:
                blob_container.delete_blob(file_path)
        except Exception:
            print(f"not found in {containerdocs}")


def remove_all_blobs_from_container(
    container_name,
    storage_account,
    storage_creds,
    verbose=False,
):
    if verbose:
        print(f"Removing all blobs from container {container_name}")
    blob_service = BlobServiceClient(
        account_url=f"https://{storage_account}.blob.core.windows.net",
        credential=storage_creds,
    )
    blob_container = blob_service.get_container_client(container_name)
    if blob_container.exists():
        try:
            blobs = blob_container.list_blobs()
            for blob in blobs:
                blob_container.delete_blob(blob.name)
        except Exception as e:
            print(f"Error occurred while deleting blobs: {str(e)}")
