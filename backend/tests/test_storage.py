from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from penalty_app.storage import LocalProofStorage, UploadSlotError


class LocalProofStorageTests(unittest.TestCase):
    def test_upload_slot_is_single_use_and_owned(self) -> None:
        with TemporaryDirectory() as directory:
            storage = LocalProofStorage(Path(directory))
            slot = storage.create_slot(
                owner_user_id="user_a",
                content_type="image/jpeg",
            )
            storage.upload(
                token=slot.token,
                content_type="image/jpeg",
                body=b"image",
            )

            self.assertTrue(storage.path_for(slot.image_key).is_file())
            storage.require_uploaded(image_key=slot.image_key, owner_user_id="user_a")

            with self.assertRaises(UploadSlotError):
                storage.upload(
                    token=slot.token,
                    content_type="image/jpeg",
                    body=b"replacement",
                )
            with self.assertRaises(UploadSlotError):
                storage.require_uploaded(
                    image_key=slot.image_key,
                    owner_user_id="user_b",
                )


if __name__ == "__main__":
    unittest.main()
