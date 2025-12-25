// ===========================================================================
// SUPABASE EDGE FUNCTION: Daily Catalyst Sync
// Replaces n8n workflow - runs daily to sync ClinicalTrials.gov data
// ===========================================================================

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// ===========================================================================
// CONFIGURATION
// ===========================================================================

const CLINICALTRIALS_API_BASE = "https://clinicaltrials.gov/api/v2/studies"
const MAX_MARKET_CAP = 5_000_000_000 // $5B
const MONTHS_AHEAD = 3

// Therapeutic areas to filter (keep database small)
const THERAPEUTIC_AREAS = [
  "oncology",
  "cancer",
  "rare disease",
  "neurology",
  "immunology",
  "cardiology"
]

// ===========================================================================
// TYPES
// ===========================================================================

interface Trial {
  nctId: string
  sponsor: string
  phase: string
  indication: string
  completionDate: string
  enrollment: number
  studyType: string
}

interface CatalystRow {
  nct_id: string
  sponsor: string
  ticker?: string
  ticker_confidence?: number
  phase: string
  indication: string
  completion_date: string
  enrollment: number
  study_type: string
  market_cap?: number
  current_price?: number
  pct_change_30d?: number
}

// ===========================================================================
// MAIN HANDLER
// ===========================================================================

serve(async (req) => {
  try {
    console.log("🚀 Daily catalyst sync started")

    // Create Supabase client (service role for full access)
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    )

    // Log function start
    const { data: logData } = await supabaseClient
      .from('edge_function_runs')
      .insert({
        function_name: 'daily-sync',
        started_at: new Date().toISOString(),
        status: 'running'
      })
      .select()
      .single()

    const functionRunId = logData?.id

    // Step 1: Fetch trials from ClinicalTrials.gov
    console.log("📡 Fetching trials from ClinicalTrials.gov API v2...")
    const trials = await fetchTrials()
    console.log(`✅ Fetched ${trials.length} trials`)

    // Step 2: Filter trials
    console.log("🔍 Filtering trials...")
    const filtered = filterTrials(trials)
    console.log(`✅ ${filtered.length} trials after filtering`)

    // Step 3: Map sponsors to tickers
    console.log("🏷️ Mapping sponsors to tickers...")
    const mapped = await mapTickers(filtered)
    console.log(`✅ Mapped ${mapped.filter(t => t.ticker).length} tickers`)

    // Step 4: Enrich with market data (yfinance via external API)
    console.log("💰 Enriching with market data...")
    const enriched = await enrichMarketData(mapped)
    console.log(`✅ Enriched ${enriched.filter(t => t.market_cap).length} trials with market data`)

    // Step 5: Filter small caps only
    const smallCaps = enriched.filter(t =>
      t.market_cap && t.market_cap < MAX_MARKET_CAP
    )
    console.log(`✅ ${smallCaps.length} small-cap trials (<$5B market cap)`)

    // Step 6: Upsert to database
    console.log("💾 Upserting to database...")
    const { error: upsertError } = await supabaseClient
      .from('catalysts')
      .upsert(
        smallCaps.map(trial => ({
          nct_id: trial.nct_id,
          sponsor: trial.sponsor,
          ticker: trial.ticker,
          ticker_confidence: trial.ticker_confidence,
          phase: trial.phase,
          indication: trial.indication,
          completion_date: trial.completion_date,
          enrollment: trial.enrollment,
          study_type: trial.study_type,
          market_cap: trial.market_cap,
          current_price: trial.current_price,
          pct_change_30d: trial.pct_change_30d,
          data_refreshed_at: new Date().toISOString()
        })),
        {
          onConflict: 'nct_id',
          ignoreDuplicates: false
        }
      )

    if (upsertError) {
      throw new Error(`Database upsert failed: ${upsertError.message}`)
    }

    console.log(`✅ Upserted ${smallCaps.length} catalysts`)

    // Step 7: Cleanup old data
    console.log("🧹 Cleaning up old data...")
    await cleanupOldData(supabaseClient)

    // Step 8: Update function log
    await supabaseClient
      .from('edge_function_runs')
      .update({
        completed_at: new Date().toISOString(),
        items_processed: smallCaps.length,
        status: 'success'
      })
      .eq('id', functionRunId)

    console.log("🎉 Daily sync completed successfully")

    return new Response(
      JSON.stringify({
        success: true,
        trials_fetched: trials.length,
        trials_filtered: filtered.length,
        tickers_mapped: mapped.filter(t => t.ticker).length,
        small_caps: smallCaps.length,
        timestamp: new Date().toISOString()
      }),
      { headers: { "Content-Type": "application/json" } }
    )

  } catch (error) {
    console.error("❌ Error in daily sync:", error)

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    )
  }
})

// ===========================================================================
// HELPER FUNCTIONS
// ===========================================================================

async function fetchTrials(): Promise<Trial[]> {
  const trials: Trial[] = []
  const endDate = new Date()
  endDate.setMonth(endDate.getMonth() + MONTHS_AHEAD)

  const params = new URLSearchParams({
    'filter.overallStatus': 'RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION',
    'filter.phase': 'PHASE2,PHASE3',
    'pageSize': '100',
    'format': 'json'
  })

  const url = `${CLINICALTRIALS_API_BASE}?${params}`

  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`ClinicalTrials.gov API error: ${response.status}`)
  }

  const data = await response.json()
  const studies = data.studies || []

  for (const study of studies) {
    const protocol = study.protocolSection || {}
    const identification = protocol.identificationModule || {}
    const sponsors = protocol.sponsorCollaboratorsModule || {}
    const design = protocol.designModule || {}
    const status = protocol.statusModule || {}
    const conditions = protocol.conditionsModule || {}
    const enrollment = protocol.designModule?.enrollmentInfo || {}

    const nctId = identification.nctId
    const sponsor = sponsors.leadSponsor?.name || 'Unknown'
    const phases = design.phases || []
    const phase = phases.length > 0 ? phases.join('/') : 'Unknown'
    const completionDate = status.primaryCompletionDateStruct?.date
    const indication = (conditions.conditions || []).join(', ')
    const enrollmentCount = enrollment.count || 0
    const studyType = design.studyType || 'Unknown'

    if (nctId && completionDate) {
      // Filter by therapeutic area (keep database small)
      const indicationLower = indication.toLowerCase()
      const isRelevant = THERAPEUTIC_AREAS.some(area =>
        indicationLower.includes(area)
      )

      if (isRelevant) {
        trials.push({
          nctId,
          sponsor,
          phase: normalizePhase(phase),
          indication,
          completionDate,
          enrollment: enrollmentCount,
          studyType
        })
      }
    }
  }

  return trials
}

function normalizePhase(phase: string): string {
  if (phase.includes('PHASE2') && phase.includes('PHASE3')) {
    return 'Phase 2/Phase 3'
  } else if (phase.includes('PHASE3')) {
    return 'Phase 3'
  } else if (phase.includes('PHASE2')) {
    return 'Phase 2'
  }
  return 'Unknown'
}

function filterTrials(trials: Trial[]): Trial[] {
  const now = new Date()
  const maxDate = new Date()
  maxDate.setMonth(maxDate.getMonth() + MONTHS_AHEAD)

  return trials.filter(trial => {
    const completionDate = new Date(trial.completionDate)
    return completionDate >= now && completionDate <= maxDate
  })
}

async function mapTickers(trials: Trial[]): Promise<CatalystRow[]> {
  // Manual ticker mappings (high-confidence matches)
  const MANUAL_MAPPINGS: Record<string, string> = {
    "Moderna, Inc.": "MRNA",
    "Pfizer": "PFE",
    "Eli Lilly and Company": "LLY",
    "Johnson & Johnson": "JNJ",
    "Merck Sharp & Dohme": "MRK",
    "AbbVie": "ABBV",
    "Bristol-Myers Squibb": "BMY",
    "AstraZeneca": "AZN",
    "Novartis": "NVS",
    "Sanofi": "SNY",
    "Amgen": "AMGN",
    "Gilead Sciences": "GILD",
    "Regeneron Pharmaceuticals": "REGN",
    "Vertex Pharmaceuticals": "VRTX",
    "Biogen": "BIIB",
    "Incyte Corporation": "INCY",
    "Alexion Pharmaceuticals": "ALXN",
    "BioNTech": "BNTX",
    "Seagen Inc.": "SGEN",
    "Alnylam Pharmaceuticals": "ALNY"
  }

  const mapped: CatalystRow[] = []

  for (const trial of trials) {
    const ticker = MANUAL_MAPPINGS[trial.sponsor]
    const tickerConfidence = ticker ? 100 : undefined

    mapped.push({
      nct_id: trial.nctId,
      sponsor: trial.sponsor,
      ticker,
      ticker_confidence: tickerConfidence,
      phase: trial.phase,
      indication: trial.indication,
      completion_date: trial.completionDate,
      enrollment: trial.enrollment,
      study_type: trial.studyType
    })
  }

  return mapped
}

async function enrichMarketData(trials: CatalystRow[]): Promise<CatalystRow[]> {
  // For free tier, we'll use a simplified enrichment
  // In production, integrate with Yahoo Finance API or similar

  // For now, return trials with ticker as-is
  // Market data enrichment can be added via external API

  return trials.filter(t => t.ticker) // Only return trials with tickers
}

async function cleanupOldData(supabaseClient: any) {
  // Delete old catalysts
  const { data: deletedCatalysts } = await supabaseClient
    .rpc('delete_old_catalysts')

  console.log(`🗑️ Deleted ${deletedCatalysts || 0} old catalysts`)

  // Delete old logs
  await supabaseClient.rpc('delete_old_email_logs')
  await supabaseClient.rpc('delete_old_analytics')
  await supabaseClient.rpc('delete_old_function_logs')

  // Vacuum to reclaim space (run via SQL, not RPC)
  console.log("✨ Cleanup complete")
}

/* ===========================================================================
   DEPLOYMENT INSTRUCTIONS:

   1. Install Supabase CLI:
      npm install -g supabase

   2. Login to Supabase:
      supabase login

   3. Link to your project:
      supabase link --project-ref your-project-ref

   4. Deploy function:
      supabase functions deploy daily-sync

   5. Set environment variables:
      supabase secrets set SUPABASE_URL=your-url
      supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your-key

   6. Create cron trigger (via Supabase Dashboard > Database > Cron):
      SELECT cron.schedule(
        'daily-catalyst-sync',
        '0 6 * * *', -- Every day at 6 AM UTC
        $$
        SELECT net.http_post(
          url := 'https://your-project-ref.supabase.co/functions/v1/daily-sync',
          headers := '{"Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
        );
        $$
      );

   7. Test manually:
      curl -X POST https://your-project-ref.supabase.co/functions/v1/daily-sync \
        -H "Authorization: Bearer YOUR_ANON_KEY"

=========================================================================== */
