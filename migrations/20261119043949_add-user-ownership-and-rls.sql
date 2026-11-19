-- ============================================================================
-- Migration: Enforce user ownership (user_id), automatic owner stamping,
-- owner-only RLS policies, and create user-owned farms & assessments tables.
-- ============================================================================

-- 1. Trigger helpers for automatic user_id assignment and owner immutability
CREATE OR REPLACE FUNCTION public.set_record_owner_user_id()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF auth.uid() IS NOT NULL THEN
    NEW.user_id := auth.uid();
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.prevent_record_owner_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'user_id cannot be changed';
  END IF;
  RETURN NEW;
END;
$$;

-- 2. Harden existing public.crop_advisories table for strict per-user isolation
DELETE FROM public.crop_advisories WHERE user_id IS NULL;

ALTER TABLE public.crop_advisories
  DROP CONSTRAINT IF EXISTS crop_advisories_user_id_fkey;

ALTER TABLE public.crop_advisories
  ALTER COLUMN user_id SET DEFAULT auth.uid(),
  ALTER COLUMN user_id SET NOT NULL,
  ADD CONSTRAINT crop_advisories_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_crop_advisories_user_created
  ON public.crop_advisories (user_id, created_at DESC);

DROP POLICY IF EXISTS "anyone can read crop advisories" ON public.crop_advisories;
DROP POLICY IF EXISTS "authenticated users can insert own advisories" ON public.crop_advisories;
DROP POLICY IF EXISTS "owners can update own advisories" ON public.crop_advisories;
DROP POLICY IF EXISTS "owners can delete own advisories" ON public.crop_advisories;

ALTER TABLE public.crop_advisories ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.crop_advisories FROM anon;
REVOKE ALL ON public.crop_advisories FROM authenticated;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.crop_advisories TO authenticated;

CREATE POLICY "crop_advisories_select_own" ON public.crop_advisories
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));

CREATE POLICY "crop_advisories_insert_own" ON public.crop_advisories
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "crop_advisories_update_own" ON public.crop_advisories
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "crop_advisories_delete_own" ON public.crop_advisories
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()));

DROP TRIGGER IF EXISTS crop_advisories_set_owner ON public.crop_advisories;
CREATE TRIGGER crop_advisories_set_owner
  BEFORE INSERT ON public.crop_advisories
  FOR EACH ROW
  EXECUTE FUNCTION public.set_record_owner_user_id();

DROP TRIGGER IF EXISTS crop_advisories_prevent_owner_change ON public.crop_advisories;
CREATE TRIGGER crop_advisories_prevent_owner_change
  BEFORE UPDATE ON public.crop_advisories
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_record_owner_change();

-- 3. Create user-owned public.farms table
CREATE TABLE IF NOT EXISTS public.farms (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  farm_name         TEXT NOT NULL,
  village           TEXT,
  district          TEXT,
  state             TEXT,
  latitude          DOUBLE PRECISION NOT NULL,
  longitude         DOUBLE PRECISION NOT NULL,
  crop_name         TEXT DEFAULT 'Tomato',
  area_acres        NUMERIC(8, 2),
  plot_length_m     NUMERIC(10, 2),
  plot_width_m      NUMERIC(10, 2),
  boundary_geojson  JSONB,
  sowing_date       TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_farms_user_created
  ON public.farms (user_id, created_at DESC);

ALTER TABLE public.farms ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.farms FROM anon;
REVOKE ALL ON public.farms FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.farms TO authenticated;

CREATE POLICY "farms_select_own" ON public.farms
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));

CREATE POLICY "farms_insert_own" ON public.farms
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "farms_update_own" ON public.farms
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "farms_delete_own" ON public.farms
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()));

CREATE TRIGGER farms_set_owner
  BEFORE INSERT ON public.farms
  FOR EACH ROW
  EXECUTE FUNCTION public.set_record_owner_user_id();

CREATE TRIGGER farms_prevent_owner_change
  BEFORE UPDATE ON public.farms
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_record_owner_change();

CREATE TRIGGER farms_updated_at
  BEFORE UPDATE ON public.farms
  FOR EACH ROW
  EXECUTE FUNCTION system.update_updated_at();

-- Recursion-safe SECURITY DEFINER helper to verify farm ownership from assessments RLS
CREATE OR REPLACE FUNCTION public.owns_farm(target_farm_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.farms
    WHERE id = target_farm_id
      AND user_id = (SELECT auth.uid())
  );
$$;

REVOKE ALL ON FUNCTION public.owns_farm(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.owns_farm(UUID) TO authenticated;

-- 4. Create user-owned public.assessments table
CREATE TABLE IF NOT EXISTS public.assessments (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  farm_id           UUID REFERENCES public.farms(id) ON DELETE SET NULL,
  crop_name         TEXT NOT NULL,
  growth_stage      TEXT,
  assessment_date   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  image_filename    TEXT,
  predicted_disease TEXT,
  model_confidence  NUMERIC(5, 4),
  crop_status       TEXT,
  soil_score        INTEGER CHECK (soil_score IS NULL OR soil_score BETWEEN 0 AND 100),
  soil_data         JSONB,
  weather_data      JSONB,
  risk_score        INTEGER CHECK (risk_score IS NULL OR risk_score BETWEEN 0 AND 100),
  risk_level        TEXT,
  advisory          JSONB,
  details           JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessments_user_date
  ON public.assessments (user_id, assessment_date DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_assessments_farm_date
  ON public.assessments (farm_id, assessment_date DESC);

ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.assessments FROM anon;
REVOKE ALL ON public.assessments FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.assessments TO authenticated;

CREATE POLICY "assessments_select_own" ON public.assessments
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));

CREATE POLICY "assessments_insert_own" ON public.assessments
  FOR INSERT TO authenticated
  WITH CHECK (
    user_id = (SELECT auth.uid())
    AND (farm_id IS NULL OR public.owns_farm(farm_id))
  );

CREATE POLICY "assessments_update_own" ON public.assessments
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (
    user_id = (SELECT auth.uid())
    AND (farm_id IS NULL OR public.owns_farm(farm_id))
  );

CREATE POLICY "assessments_delete_own" ON public.assessments
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()));

CREATE TRIGGER assessments_set_owner
  BEFORE INSERT ON public.assessments
  FOR EACH ROW
  EXECUTE FUNCTION public.set_record_owner_user_id();

CREATE TRIGGER assessments_prevent_owner_change
  BEFORE UPDATE ON public.assessments
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_record_owner_change();

CREATE TRIGGER assessments_updated_at
  BEFORE UPDATE ON public.assessments
  FOR EACH ROW
  EXECUTE FUNCTION system.update_updated_at();
