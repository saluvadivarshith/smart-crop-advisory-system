-- Create public.crop_advisories table for CropSense Smart Crop Advisory System
CREATE TABLE public.crop_advisories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  farm_name TEXT NOT NULL,
  village TEXT NOT NULL,
  district TEXT NOT NULL,
  state TEXT NOT NULL,
  crop_name TEXT NOT NULL,
  growth_stage TEXT NOT NULL,
  area_acres NUMERIC(6, 2) NOT NULL DEFAULT 1.00,
  predicted_disease TEXT,
  model_confidence NUMERIC(5, 4),
  soil_score INTEGER CHECK (soil_score BETWEEN 0 AND 100),
  risk_score INTEGER CHECK (risk_score BETWEEN 0 AND 100),
  risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MODERATE', 'HIGH')),
  recommended_action TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_crop_advisories_crop_risk ON public.crop_advisories (crop_name, risk_level, created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.crop_advisories ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "anyone can read crop advisories" ON public.crop_advisories
  FOR SELECT TO anon, authenticated
  USING (true);

CREATE POLICY "authenticated users can insert own advisories" ON public.crop_advisories
  FOR INSERT TO authenticated
  WITH CHECK (user_id IS NULL OR user_id = (SELECT auth.uid()));

CREATE POLICY "owners can update own advisories" ON public.crop_advisories
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "owners can delete own advisories" ON public.crop_advisories
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()));

-- Grant SQL privileges
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.crop_advisories TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.crop_advisories TO authenticated;

-- Auto-update updated_at column via InsForge built-in trigger function
CREATE TRIGGER crop_advisories_updated_at
  BEFORE UPDATE ON public.crop_advisories
  FOR EACH ROW
  EXECUTE FUNCTION system.update_updated_at();

-- Seed sample Smart Crop Advisory records
INSERT INTO public.crop_advisories (
  farm_name, village, district, state, crop_name, growth_stage, area_acres,
  predicted_disease, model_confidence, soil_score, risk_score, risk_level, recommended_action
) VALUES
  (
    'Raju North Plot', 'Parkal', 'Hanamkonda', 'Telangana',
    'Tomato', 'flowering', 2.50,
    'Early Blight', 0.9800, 58, 78, 'HIGH',
    'Remove infected lower leaves showing target-ring spots, apply straw mulch to prevent rain splash, avoid overhead watering, and apply 25% top-dressing Urea after weeding.'
  ),
  (
    'Lakshmi Black-Soil Field', 'Nandigama', 'NTR', 'Andhra Pradesh',
    'Chilli', 'vegetative', 1.75,
    'Healthy', 0.9650, 82, 22, 'LOW',
    'Leaf canopy is healthy and soil fertility is balanced (82/100). Install yellow and blue sticky traps at crop height to monitor thrips and whiteflies.'
  ),
  (
    'Venkatesh Tank-Fed Plot', 'Armoor', 'Nizamabad', 'Telangana',
    'Maize (Corn)', 'vegetative', 3.00,
    'Common Rust', 0.9830, 64, 52, 'MODERATE',
    'Monitor reddish-brown rust pustules on lower leaves during cool dewy mornings; apply Zinc Sulphate (25 kg/ha) for deficient soil Zn and maintain ridge drainage.'
  ),
  (
    'Srinivas Ridge Plot', 'Zaheerabad', 'Sangareddy', 'Telangana',
    'Potato', 'flowering', 1.25,
    'Late Blight', 0.8915, 61, 84, 'HIGH',
    'High humidity (RH >= 90%) favors rapid Late Blight spread. Destroy blighted foliage away from field, irrigate only in morning hours at plant base, and consult local KVK immediately.'
  );
