#! /bin/bash -xu
{
  # newline
  n=$'\n'
  declare -A LOG_LEVELS
  # https://en.wikipedia.org/wiki/Syslog#Severity_level
  LOG_LEVELS=([0]="emerg" [1]="alert" [2]="crit" [3]="err" [4]="warning" [5]="notice" [6]="info" [7]="debug")
  # Scan all files in here
  SRC_DIR="$(echo $PWD)"
  # Log file, file where we tell what events have been processed.
  LOG_FILE="/config/logs/scd.log"
  # If file is ok, list it here
  GOOD_FILES="/config/logs/verified_files.log"
  # Put files here if unsure
  QUARANTINE="/Quarantine/"
  # This is where the hybrid analysis script lives
  HA_SCRIPT="/config/scripts/VxAPI/vxapi.py"
  # Sleep for this long when waiting for VT API to chill
  # 1 call every 173s = 500 API calls/day
  SLEEP_SEC=10
  # Try for this many times to upload the file
  SCAN_ATTEMPTS=8

  function show_help ()
    {
      # Show help and exit
      echo "filename.sh [-vh]
      optional arguments:
        -h, --help      Show this message and exit
        -v, --verbose   Verbosity level:
                          0: emerg, 1: alert,
                          2: crit,  3: err,
                          4: warn,  5: notice,
                          6: info*, 7: debug"
      exit 0
    }

  # Modified from https://stackoverflow.com/a/33597663
  function .log () {
      local LEVEL=${1}
      shift
      if [ ${__VERBOSE} -ge ${LEVEL} ]; then
        # Log the date and info level as "[YYYY-MM-DDTHH:MM:SS-LEVEL] MESSAGE"
        echo "[$(date +%Y-%m-%dT%H:%M:%S)-${LOG_LEVELS[$LEVEL]}]" "$@" >> $LOG_FILE
      fi
    }

    # Check for a verbosity flag
    while (( $# )); do
      case $1 in
        # Parse any optional flags
          -h|-\?|--help) show_help;;
          -v|--verbose) _USER_VERB=$((_USER_VERB + 1));;  # Each -v adds 1 to verbosity
          *) .log "$1 unexpected"
      esac
      shift
    done

  # If user didn't specify -v, use default of 6
  __VERBOSE="${_USER_VERB:-6}"

  .log 7 "Using script at $HA_SCRIPT"

  # Scan the files
  # Get a list of files to check
  IFS=$'\n'
  files=($(find $SRC_DIR -type f))
  touch $GOOD_FILES
  readarray cleared_files < $GOOD_FILES
  unset IFS
  # Upload each file
  for entry in "${files[@]}"; do
    .log 7 "$entry"
    # Check if file already scanned
    IFS=$'\n'
    if [[ "${IFS}${cleared_files[*]}${IFS}" =~ "${IFS}'${entry}'${IFS}" ]]; then
        # file previously scanned, skip analysis
        .log 6 "'$entry' already scanned"
        continue
    fi
    unset IFS
    # File not scanned, upload and log
    .log 6 "Uploading '$entry' to hybrid-analysis.com"
    # A high verbosity response breaks jq parsing, so it is only done once
    # Sleep for 5 sec after to not overload the API
    #.log 7 $("$HA_SCRIPT" scan_file "$entry" all -v; sleep 5) #Currently skipped because log will include API key
    # Grab the ID and check if it is malicious
    response=$("$HA_SCRIPT" scan_file "$entry" all )
    .log 7 "$response"
    if [[ $(echo $response | jq -r ".id") != 'null' ]]; then
      # Don't overwrite id if errored
      id=$(echo $response | jq -r ".id")
      .log 7 $id
    fi
    if [[ $(echo $response | jq -r ".sha256") != 'null' ]]; then
      # Don't overwrite sha256 if errored
      sha256=$(echo $response | jq -r ".sha256")
      .log 7 $sha256
    fi
    if [[ $(echo $response | jq -r ".finished") != 'null' ]]; then
      # Don't overwrite finished if errored
      finished=$(echo $response | jq -r ".finished")
      .log 7 $finished
    fi
    attempt=0
     while [[ $attempt -lt $SCAN_ATTEMPTS ]] && [[ $finished != "true" ]]; do
        # State what attempt we're on
        .log 7 "attempt $attempt"
        if [[ $attempt -gt 0 ]]; then
          # Don't retry immediately
          .log 6 "sleeping for $SLEEP_SEC seconds before retrying"
          sleep $SLEEP_SEC
          # Sleep until midnight
          #__TO_SLEEP=$(( $(date -f - +%s- <<< "tomorrow 00:01"$'\nnow') 0 ))
          #.log 5 "sleeping '$__TO_SLEEP' seconds until midnight"
          #sleep $__TO_SLEEP
        fi
        # Get a quick scan
        scan=$("$HA_SCRIPT" scan_get_result $id)
        .log 7 $scan
        # Check if finished
        finished=$(echo $scan | jq -r ".finished")
        attempt+=1
      done
    # Get a summary of the file
    summary=$("$HA_SCRIPT" report_get_summary $sha256)
    .log 7 $summary
    if [[ $finished == "true" ]]; then
        # Done scanning, analyze
        # TODO: is it "no specific threat" or "no-specific-threat"
        # verdict has "malicious", "suspicious", "no specific threat", "unknown", "null"
        verdict=$(echo $summary | jq -r ".verdict")
        if [[ $verdict == "no specific threat" ]]; then
              # Grab the path to the parent dir 
              parent=$(dirname "$entry")
              # Note the file is good
              # Use absolute path
              (echo \"$(cd "$parent" && pwd)/$(basename "$entry")\") >> $GOOD_FILES
              # Make note of the verification time
              .log 7 "'$entry' verified $(date +%s --date=$(echo $summary | jq -r ".analysis_start_time")) seconds after epoch."
        elif [[ $verdict == "null" ]] || [[ $verdict == "unknown" ]]; then
            # Quarantine
            .log 6 "'$entry' verdict is $verdict. Will Quarantine and log summary"
            .log 4 $summary
            cp "$entry" "$QUARANTINE" && rm "$entry"
            .log 6 "Quarantine move successful"
        else
            # Bad file, delete and log
            .log 1 "VIRUS FOUND:'$entry' deemed $verdict! Attempting deletion"
            .log 4 $summary
            rm "$entry"
            .log 6 "Deletion successful"
            exit 0
        fi
    else
        # Didn't finish, something wrong?
        .log 6 "'$entry' could not be scanned in $attempt attempts. Will Quarantine and log summary"
        .log 4 $summary
        cp "$entry" "$QUARANTINE" && rm "$entry"
    fi
    .log 6 "sleeping for $SLEEP_SEC seconds"
    # Always sleep
    sleep $SLEEP_SEC
  done
  .log 6 "done scanning"
} &
