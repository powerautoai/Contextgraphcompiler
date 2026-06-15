pipeline {
  agent none

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  parameters {
    string(name: 'WINDOWS_LABEL', defaultValue: 'windows && cgc', description: 'Jenkins label for the Windows build node')
    string(name: 'MACOS_LABEL', defaultValue: 'macos && cgc', description: 'Jenkins label for the macOS build node')
    string(name: 'LINUX_LABEL', defaultValue: 'linux && cgc', description: 'Jenkins label for the Linux build node')
    string(name: 'AGGREGATOR_LABEL', defaultValue: 'linux && cgc', description: 'Jenkins label for the final matrix aggregation node')
    string(name: 'WINDOWS_PYTHON', defaultValue: 'python', description: 'Python command on the Windows node')
    string(name: 'MACOS_PYTHON', defaultValue: 'python3', description: 'Python command on the macOS node')
    string(name: 'LINUX_PYTHON', defaultValue: 'python3', description: 'Python command on the Linux node')
  }

  environment {
    M84_REPORT_DIR = 'ci/m84-reports'
    M84_BUILD_DIR = 'ci/m84-builds'
    M84_GATE_DIR = 'ci/m84-gate'
    M84_DIST_DIR = 'CGC_Release/dist'
  }

  stages {
    stage('Checkout') {
      agent { label "${params.AGGREGATOR_LABEL}" }
      steps {
        checkout scm
      }
    }

    stage('Build Matrix') {
      parallel {
        stage('Build Windows') {
          agent { label "${params.WINDOWS_LABEL}" }
          steps {
            checkout scm
            bat """
              if not exist %M84_REPORT_DIR% mkdir %M84_REPORT_DIR%
              if not exist %M84_BUILD_DIR%\\windows mkdir %M84_BUILD_DIR%\\windows
              ${params.WINDOWS_PYTHON} -m pip install --upgrade pip
              ${params.WINDOWS_PYTHON} -m pip install nuitka fastapi uvicorn requests pyyaml jsonschema
              ${params.WINDOWS_PYTHON} -m app.cli.cgc build ^
                --output-dir "%WORKSPACE%\\%M84_BUILD_DIR%\\windows" ^
                --json ^
                --report-file "%WORKSPACE%\\%M84_REPORT_DIR%\\host-build-windows.json" ^
                --aggregate-dir "%WORKSPACE%\\%M84_REPORT_DIR%"
            """
            stash name: 'm84-report-windows', includes: 'ci/m84-reports/windows.json,ci/m84-reports/host-build-windows.json', allowEmpty: true
            stash name: 'm84-output-windows', includes: 'ci/m84-builds/windows/**/*', allowEmpty: true
            archiveArtifacts artifacts: 'ci/m84-reports/windows.json,ci/m84-reports/host-build-windows.json,ci/m84-builds/windows/**/*', fingerprint: true, allowEmptyArchive: true
          }
        }

        stage('Build macOS') {
          agent { label "${params.MACOS_LABEL}" }
          steps {
            checkout scm
            sh '''
              mkdir -p "${M84_REPORT_DIR}" "${M84_BUILD_DIR}/macos"
              ${MACOS_PYTHON} -m pip install --upgrade pip
              ${MACOS_PYTHON} -m pip install nuitka fastapi uvicorn requests pyyaml jsonschema
              ${MACOS_PYTHON} -m app.cli.cgc build \
                --output-dir "${WORKSPACE}/${M84_BUILD_DIR}/macos" \
                --json \
                --report-file "${WORKSPACE}/${M84_REPORT_DIR}/host-build-macos.json" \
                --aggregate-dir "${WORKSPACE}/${M84_REPORT_DIR}"
            '''
            stash name: 'm84-report-macos', includes: 'ci/m84-reports/macos.json,ci/m84-reports/host-build-macos.json', allowEmpty: true
            stash name: 'm84-output-macos', includes: 'ci/m84-builds/macos/**/*', allowEmpty: true
            archiveArtifacts artifacts: 'ci/m84-reports/macos.json,ci/m84-reports/host-build-macos.json,ci/m84-builds/macos/**/*', fingerprint: true, allowEmptyArchive: true
          }
        }

        stage('Build Linux') {
          agent { label "${params.LINUX_LABEL}" }
          steps {
            checkout scm
            sh '''
              mkdir -p "${M84_REPORT_DIR}" "${M84_BUILD_DIR}/linux"
              ${LINUX_PYTHON} -m pip install --upgrade pip
              ${LINUX_PYTHON} -m pip install nuitka fastapi uvicorn requests pyyaml jsonschema
              ${LINUX_PYTHON} -m app.cli.cgc build \
                --output-dir "${WORKSPACE}/${M84_BUILD_DIR}/linux" \
                --json \
                --report-file "${WORKSPACE}/${M84_REPORT_DIR}/host-build-linux.json" \
                --aggregate-dir "${WORKSPACE}/${M84_REPORT_DIR}"
            '''
            stash name: 'm84-report-linux', includes: 'ci/m84-reports/linux.json,ci/m84-reports/host-build-linux.json', allowEmpty: true
            stash name: 'm84-output-linux', includes: 'ci/m84-builds/linux/**/*', allowEmpty: true
            archiveArtifacts artifacts: 'ci/m84-reports/linux.json,ci/m84-reports/host-build-linux.json,ci/m84-builds/linux/**/*', fingerprint: true, allowEmptyArchive: true
          }
        }
      }
    }

    stage('Aggregate M8.4 Gate') {
      agent { label "${params.AGGREGATOR_LABEL}" }
      steps {
        deleteDir()
        checkout scm
        script {
          ['m84-report-windows', 'm84-report-macos', 'm84-report-linux', 'm84-output-windows', 'm84-output-macos', 'm84-output-linux'].each { stashName ->
            try {
              unstash stashName
            } catch (Exception ignored) {
              echo "No stash available for ${stashName}"
            }
          }
        }
        sh '''
          mkdir -p "${M84_REPORT_DIR}" "${M84_GATE_DIR}"
          python3 -m pip install --upgrade pip
          python3 -m pip install pyyaml jsonschema
          python3 scripts/ci/write_build_matrix.py \
            --input-dir "${WORKSPACE}/${M84_REPORT_DIR}" \
            --required-platform windows \
            --required-platform macos \
            --required-platform linux
          python3 scripts/ci/render_m84_gate_config.py \
            --base-config "${WORKSPACE}/CGC_Release/m8_gate.yaml" \
            --output-config "${WORKSPACE}/${M84_REPORT_DIR}/m84-only.yaml" \
            --matrix-dir "${WORKSPACE}/${M84_REPORT_DIR}" \
            --dist-dir "${WORKSPACE}/${M84_DIST_DIR}"
          python3 scripts/ci/collect_release_dist.py \
            --matrix-dir "${WORKSPACE}/${M84_REPORT_DIR}" \
            --build-artifacts-dir "${WORKSPACE}/${M84_BUILD_DIR}" \
            --dist-dir "${WORKSPACE}/${M84_DIST_DIR}" \
            --release-assets-dir "${WORKSPACE}/${M84_DIST_DIR}/release_assets" \
            --required-platform windows \
            --required-platform macos \
            --required-platform linux
          python3 CGC_Release/m8_gate.py \
            --output-dir "${WORKSPACE}/${M84_GATE_DIR}" \
            --config "${WORKSPACE}/${M84_REPORT_DIR}/m84-only.yaml" \
            --print-report
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'ci/m84-reports/**/*,ci/m84-builds/**/*,ci/m84-gate/**/*,CGC_Release/dist/**/*', fingerprint: true, allowEmptyArchive: true
        }
      }
    }
  }
}
