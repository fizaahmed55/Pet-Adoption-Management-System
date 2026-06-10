UPDATE pet_image
SET image_url = 'assets/buddy.jpg'
WHERE pet_id = 1;

UPDATE pet_image
SET image_url = 'assets/luna.jpg'
WHERE pet_id = 2;

UPDATE pet_image
SET image_url = 'assets/max.jpg'
WHERE pet_id = 3;

UPDATE pet_image
SET image_url = 'assets/milo.jpg'
WHERE pet_id = 4;

COMMIT;