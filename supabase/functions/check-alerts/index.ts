// ===========================================================================
// SUPABASE EDGE FUNCTION: Check Alerts
// Monitors saved searches and sends notifications for new catalyst matches
// Runs daily at 9 AM ET (14:00 UTC)
// ===========================================================================

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// ===========================================================================
// TYPES
// ===========================================================================

interface SavedSearch {
  id: string
  user_id: string
  name: string
  query_params: Record<string, any>
  notification_channels: string[]
  last_checked: string | null
  active: boolean
}

interface Catalyst {
  id: string
  nct_id: string
  sponsor: string
  ticker: string
  phase: string
  indication: string
  completion_date: string
  market_cap: number
  current_price: number
  enrollment: number
  created_at: string
}

interface NotificationPreferences {
  user_id: string
  max_alerts_per_day: number
  email_enabled: boolean
  sms_enabled: boolean
  slack_enabled: boolean
  phone_number?: string
  slack_webhook_url?: string
}

interface AlertMessage {
  search_name: string
  ticker: string
  sponsor: string
  phase: string
  indication: string
  completion_date: string
  days_until: number | null
  market_cap: string
  current_price: string
  enrollment: number
  nct_id: string
  catalyst_id: string
}

// ===========================================================================
// MAIN HANDLER
// ===========================================================================

serve(async (req) => {
  try {
    console.log("🔔 Check alerts started")

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
        function_name: 'check-alerts',
        started_at: new Date().toISOString(),
        status: 'running'
      })
      .select()
      .single()

    const functionRunId = logData?.id

    const stats = {
      searches_checked: 0,
      matches_found: 0,
      notifications_sent: 0,
      errors: 0
    }

    // Step 1: Fetch all active saved searches
    console.log("📋 Fetching active saved searches...")
    const { data: searches, error: searchError } = await supabaseClient
      .from('saved_searches')
      .select('*')
      .eq('active', true)

    if (searchError) {
      throw new Error(`Failed to fetch saved searches: ${searchError.message}`)
    }

    console.log(`Found ${searches?.length || 0} active saved searches`)

    // Step 2: Process each saved search
    for (const search of searches || []) {
      try {
        stats.searches_checked++

        // Find new matches since last check
        const matches = await findNewMatches(supabaseClient, search)

        if (matches.length > 0) {
          console.log(`Found ${matches.length} new matches for search "${search.name}"`)
          stats.matches_found += matches.length

          // Send notifications for each match
          for (const catalyst of matches) {
            const sent = await sendNotification(
              supabaseClient,
              search,
              catalyst
            )

            if (sent) {
              stats.notifications_sent++
            }
          }
        }

        // Update last_checked timestamp
        await supabaseClient
          .from('saved_searches')
          .update({ last_checked: new Date().toISOString() })
          .eq('id', search.id)

      } catch (error) {
        console.error(`Error processing search ${search.id}:`, error)
        stats.errors++
        continue
      }
    }

    // Step 3: Cleanup old alert notifications
    console.log("🧹 Cleaning up old alert notifications...")
    const { data: deletedCount } = await supabaseClient
      .rpc('delete_old_alert_notifications')

    console.log(`Deleted ${deletedCount || 0} old alert notifications`)

    // Step 4: Update function log
    await supabaseClient
      .from('edge_function_runs')
      .update({
        completed_at: new Date().toISOString(),
        items_processed: stats.notifications_sent,
        status: stats.errors > 0 ? 'partial' : 'success'
      })
      .eq('id', functionRunId)

    console.log("✅ Check alerts completed successfully")
    console.log(`Stats: ${JSON.stringify(stats)}`)

    return new Response(
      JSON.stringify({
        success: true,
        ...stats,
        timestamp: new Date().toISOString()
      }),
      { headers: { "Content-Type": "application/json" } }
    )

  } catch (error) {
    console.error("❌ Error in check-alerts:", error)

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

async function findNewMatches(
  supabase: any,
  search: SavedSearch
): Promise<Catalyst[]> {
  try {
    let query = supabase.from('catalysts').select('*')

    // Filter by last_checked (only new catalysts)
    if (search.last_checked) {
      query = query.gte('created_at', search.last_checked)
    }

    const params = search.query_params

    // Apply search filters
    if (params.phase) {
      query = query.eq('phase', params.phase)
    }

    if (params.max_market_cap) {
      query = query.lt('market_cap', params.max_market_cap)
    }

    if (params.min_market_cap) {
      query = query.gte('market_cap', params.min_market_cap)
    }

    if (params.therapeutic_area) {
      query = query.ilike('indication', `%${params.therapeutic_area}%`)
    }

    if (params.min_enrollment) {
      query = query.gte('enrollment', params.min_enrollment)
    }

    if (params.completion_date_start) {
      query = query.gte('completion_date', params.completion_date_start)
    }

    if (params.completion_date_end) {
      query = query.lte('completion_date', params.completion_date_end)
    }

    // Only return catalysts with tickers
    query = query.not('ticker', 'is', null)

    // Order by completion date
    query = query.order('completion_date', { ascending: true })

    const { data, error } = await query

    if (error) {
      throw new Error(`Query error: ${error.message}`)
    }

    return data || []

  } catch (error) {
    console.error(`Error finding matches for search ${search.id}:`, error)
    return []
  }
}

async function sendNotification(
  supabase: any,
  search: SavedSearch,
  catalyst: Catalyst
): Promise<boolean> {
  try {
    // Check if already notified (deduplication)
    const { data: existing } = await supabase
      .from('alert_notifications')
      .select('id')
      .eq('saved_search_id', search.id)
      .eq('catalyst_id', catalyst.id)
      .single()

    if (existing) {
      console.log(`Skipping duplicate alert for catalyst ${catalyst.id}`)
      return false
    }

    // Check user permissions and limits
    const canSend = await canSendNotification(supabase, search.user_id)
    if (!canSend) {
      console.log(`Skipping notification for user ${search.user_id} (rate limit or quiet hours)`)
      return false
    }

    // Format alert message
    const alertMessage = formatAlertMessage(catalyst, search.name)

    // Get user tier for channel restrictions
    const { data: userTier } = await supabase.rpc('get_user_tier', {
      p_user_id: search.user_id
    })

    // Send via each channel
    const sentChannels: string[] = []

    for (const channel of search.notification_channels) {
      if (channel === 'email') {
        if (await sendEmail(supabase, search.user_id, alertMessage)) {
          sentChannels.push('email')
        }
      } else if (channel === 'sms' && userTier === 'pro') {
        if (await sendSMS(supabase, search.user_id, alertMessage)) {
          sentChannels.push('sms')
        }
      } else if (channel === 'slack' && userTier === 'pro') {
        if (await sendSlack(supabase, search.user_id, alertMessage)) {
          sentChannels.push('slack')
        }
      }
    }

    // Log notification
    if (sentChannels.length > 0) {
      await supabase
        .from('alert_notifications')
        .insert({
          saved_search_id: search.id,
          catalyst_id: catalyst.id,
          user_id: search.user_id,
          channels_used: sentChannels,
          alert_content: alertMessage,
          notification_sent_at: new Date().toISOString()
        })

      console.log(`✅ Sent notification to user ${search.user_id} via ${sentChannels.join(', ')}`)
      return true
    }

    return false

  } catch (error) {
    console.error(`Error sending notification:`, error)
    return false
  }
}

async function canSendNotification(supabase: any, userId: string): Promise<boolean> {
  try {
    // Check rate limit
    const { data: canReceive } = await supabase.rpc('can_receive_alert', {
      p_user_id: userId
    })

    if (!canReceive) {
      return false
    }

    // Check quiet hours
    const { data: isQuiet } = await supabase.rpc('is_quiet_hours', {
      p_user_id: userId
    })

    return !isQuiet

  } catch (error) {
    console.error(`Error checking notification permissions:`, error)
    return true // Fail open
  }
}

function formatAlertMessage(catalyst: Catalyst, searchName: string): AlertMessage {
  // Format market cap
  const marketCapB = catalyst.market_cap / 1_000_000_000
  const marketCapStr = `$${marketCapB.toFixed(2)}B`

  // Format price
  const priceStr = catalyst.current_price ? `$${catalyst.current_price.toFixed(2)}` : 'N/A'

  // Calculate days until catalyst
  let daysUntil: number | null = null
  if (catalyst.completion_date) {
    const completionDate = new Date(catalyst.completion_date)
    const now = new Date()
    daysUntil = Math.floor((completionDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  }

  return {
    search_name: searchName,
    ticker: catalyst.ticker,
    sponsor: catalyst.sponsor,
    phase: catalyst.phase,
    indication: catalyst.indication,
    completion_date: catalyst.completion_date,
    days_until: daysUntil,
    market_cap: marketCapStr,
    current_price: priceStr,
    enrollment: catalyst.enrollment,
    nct_id: catalyst.nct_id,
    catalyst_id: catalyst.id
  }
}

async function sendEmail(
  supabase: any,
  userId: string,
  alert: AlertMessage
): Promise<boolean> {
  const sendgridApiKey = Deno.env.get('SENDGRID_API_KEY')
  if (!sendgridApiKey) {
    console.warn('SendGrid API key not configured')
    return false
  }

  try {
    // Get user email
    const { data: user } = await supabase
      .from('users')
      .select('email')
      .eq('id', userId)
      .single()

    if (!user) {
      console.error(`User ${userId} not found`)
      return false
    }

    const subject = `🚀 New Catalyst Alert: ${alert.ticker} - ${alert.search_name}`

    const htmlContent = `
      <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2 style="color: #2c3e50;">New Catalyst Match: ${alert.ticker}</h2>
        <p>Your saved search "<strong>${alert.search_name}</strong>" found a new match:</p>
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
          <h3 style="margin-top: 0; color: #495057;">${alert.ticker} - ${alert.sponsor}</h3>
          <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px 0;"><strong>Phase:</strong></td><td>${alert.phase}</td></tr>
            <tr><td style="padding: 8px 0;"><strong>Indication:</strong></td><td>${alert.indication}</td></tr>
            <tr><td style="padding: 8px 0;"><strong>Catalyst Date:</strong></td><td>${alert.completion_date}</td></tr>
            ${alert.days_until ? `<tr><td style="padding: 8px 0;"><strong>Days Until:</strong></td><td>${alert.days_until} days</td></tr>` : ''}
            <tr><td style="padding: 8px 0;"><strong>Market Cap:</strong></td><td>${alert.market_cap}</td></tr>
            <tr><td style="padding: 8px 0;"><strong>Current Price:</strong></td><td>${alert.current_price}</td></tr>
            <tr><td style="padding: 8px 0;"><strong>NCT ID:</strong></td><td><a href="https://clinicaltrials.gov/study/${alert.nct_id}">${alert.nct_id}</a></td></tr>
          </table>
        </div>
        <p style="margin-top: 30px;">
          <a href="https://biotechcatalyst.app/dashboard" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Full Details</a>
        </p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #dee2e6;">
        <p style="font-size: 12px; color: #6c757d;">
          You received this email because you have an active saved search with alerts enabled.
          <a href="https://biotechcatalyst.app/alerts">Manage your alerts</a>
        </p>
      </body>
      </html>
    `

    // Send via SendGrid
    const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sendgridApiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: user.email }] }],
        from: { email: 'alerts@biotechcatalyst.app', name: 'Biotech Catalyst Radar' },
        subject: subject,
        content: [{ type: 'text/html', value: htmlContent }]
      })
    })

    if (response.status === 202) {
      console.log(`Email sent to ${user.email}`)
      return true
    } else {
      console.error(`SendGrid error: ${response.status}`)
      return false
    }

  } catch (error) {
    console.error('Error sending email:', error)
    return false
  }
}

async function sendSMS(
  supabase: any,
  userId: string,
  alert: AlertMessage
): Promise<boolean> {
  const twilioSid = Deno.env.get('TWILIO_ACCOUNT_SID')
  const twilioToken = Deno.env.get('TWILIO_AUTH_TOKEN')
  const twilioFrom = Deno.env.get('TWILIO_FROM_NUMBER')

  if (!twilioSid || !twilioToken || !twilioFrom) {
    console.warn('Twilio credentials not configured')
    return false
  }

  try {
    // Get user phone number
    const { data: prefs } = await supabase
      .from('notification_preferences')
      .select('phone_number')
      .eq('user_id', userId)
      .single()

    if (!prefs?.phone_number) {
      console.warn(`No phone number for user ${userId}`)
      return false
    }

    // Format SMS (160 chars max)
    const smsText = `🚀 New Catalyst: ${alert.ticker} (${alert.phase}) - ${alert.completion_date}. Market Cap: ${alert.market_cap}. View: https://biotechcatalyst.app`

    // Send via Twilio
    const auth = btoa(`${twilioSid}:${twilioToken}`)
    const response = await fetch(
      `https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
          To: prefs.phone_number,
          From: twilioFrom,
          Body: smsText
        })
      }
    )

    if (response.status === 201) {
      console.log(`SMS sent to ${prefs.phone_number}`)
      return true
    } else {
      console.error(`Twilio error: ${response.status}`)
      return false
    }

  } catch (error) {
    console.error('Error sending SMS:', error)
    return false
  }
}

async function sendSlack(
  supabase: any,
  userId: string,
  alert: AlertMessage
): Promise<boolean> {
  try {
    // Get user Slack webhook
    const { data: prefs } = await supabase
      .from('notification_preferences')
      .select('slack_webhook_url')
      .eq('user_id', userId)
      .single()

    if (!prefs?.slack_webhook_url) {
      console.warn(`No Slack webhook for user ${userId}`)
      return false
    }

    // Format Slack message
    const slackPayload = {
      text: `🚀 New Catalyst Alert: ${alert.ticker}`,
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: `🚀 New Catalyst: ${alert.ticker}`
          }
        },
        {
          type: 'section',
          fields: [
            { type: 'mrkdwn', text: `*Search:*\n${alert.search_name}` },
            { type: 'mrkdwn', text: `*Phase:*\n${alert.phase}` },
            { type: 'mrkdwn', text: `*Sponsor:*\n${alert.sponsor}` },
            { type: 'mrkdwn', text: `*Catalyst Date:*\n${alert.completion_date}` },
            { type: 'mrkdwn', text: `*Market Cap:*\n${alert.market_cap}` },
            { type: 'mrkdwn', text: `*Price:*\n${alert.current_price}` }
          ]
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `*Indication:* ${alert.indication}`
          }
        },
        {
          type: 'actions',
          elements: [
            {
              type: 'button',
              text: { type: 'plain_text', text: 'View Details' },
              url: 'https://biotechcatalyst.app/dashboard'
            }
          ]
        }
      ]
    }

    const response = await fetch(prefs.slack_webhook_url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(slackPayload)
    })

    if (response.status === 200) {
      console.log(`Slack message sent to user ${userId}`)
      return true
    } else {
      console.error(`Slack webhook error: ${response.status}`)
      return false
    }

  } catch (error) {
    console.error('Error sending Slack notification:', error)
    return false
  }
}

/* ===========================================================================
   DEPLOYMENT INSTRUCTIONS:

   1. Deploy function:
      supabase functions deploy check-alerts

   2. Set environment variables:
      supabase secrets set SENDGRID_API_KEY=your-key
      supabase secrets set TWILIO_ACCOUNT_SID=your-sid
      supabase secrets set TWILIO_AUTH_TOKEN=your-token
      supabase secrets set TWILIO_FROM_NUMBER=+1234567890

   3. Create cron trigger (via Supabase Dashboard > Database > Cron):
      SELECT cron.schedule(
        'check-alerts-daily',
        '0 14 * * *', -- 9 AM ET = 14:00 UTC
        $$
        SELECT net.http_post(
          url := 'https://your-project.supabase.co/functions/v1/check-alerts',
          headers := '{"Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
        );
        $$
      );

   4. Test manually:
      curl -X POST https://your-project.supabase.co/functions/v1/check-alerts \
        -H "Authorization: Bearer YOUR_ANON_KEY"

=========================================================================== */
