-- Parallax v1.3 migration 0012
-- OPTIONAL PostGIS geospatial profile.
-- This profile is not required for the core application. Enable only after
-- compatibility is validated in the target database image.

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE user_place
  ADD COLUMN geog geography(Point, 4326);

ALTER TABLE geospatial_observation
  ADD COLUMN geog geography(Point, 4326);

UPDATE user_place
SET geog = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

UPDATE geospatial_observation
SET geog = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE OR REPLACE FUNCTION parallax_set_user_place_geog()
RETURNS trigger AS $$
BEGIN
  IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
    NEW.geog = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
  ELSE
    NEW.geog = NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION parallax_set_geospatial_observation_geog()
RETURNS trigger AS $$
BEGIN
  IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
    NEW.geog = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
  ELSE
    NEW.geog = NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_place_set_geog
BEFORE INSERT OR UPDATE OF latitude, longitude ON user_place
FOR EACH ROW
EXECUTE FUNCTION parallax_set_user_place_geog();

CREATE TRIGGER trg_geospatial_observation_set_geog
BEFORE INSERT OR UPDATE OF latitude, longitude ON geospatial_observation
FOR EACH ROW
EXECUTE FUNCTION parallax_set_geospatial_observation_geog();

CREATE INDEX idx_user_place_geog_gist
  ON user_place USING gist (geog);

CREATE INDEX idx_geospatial_observation_geog_gist
  ON geospatial_observation USING gist (geog);

COMMIT;
