*** Settings ***
Documentation     Test to validate HTML report table data against Parquet dataset.
...               Opens local HTML report, extracts table data, reads Parquet dataset,
...               optionally filters by date, and compares both for exact match.

Library           SeleniumLibrary
Library           helper.py

Suite Setup       Open Browser To Report
Suite Teardown    Close Browser

*** Variables ***
${REPORT_FILE}        ${CURDIR}/report.html
${PARQUET_FOLDER}    ${CURDIR}/parquet_data/data.parquet
${FILTER_DATE}        ${EMPTY}
${BROWSER}            chrome

*** Test Cases ***
Validate HTML Table Matches Parquet Dataset
    [Documentation]    Compare HTML table data with Parquet dataset.
    ...               Opens local HTML report, extracts table, reads Parquet with optional filtering,
    ...               and compares both datasets for exact match.
    [Tags]    data-validation    smoke
    
    Log    Step 1: Locate HTML table in report    console=True
    ${table_element}=    Get WebElement    xpath=//table[@id='results-table']
    
    Log    Step 2: Extract table data into DataFrame    console=True
    ${html_df}=    Read HTML Table To DataFrame    ${table_element}
    Log    HTML DataFrame loaded    console=True
    
    Log    Step 3: Read Parquet dataset with optional filter    console=True
    ${parquet_df}=    Read Parquet With Filter    ${PARQUET_FOLDER}    ${FILTER_DATE}
    Log    Parquet DataFrame loaded    console=True
    
    Log    Step 4: Compare DataFrames for exact match    console=True
    ${match}    ${report}=    Compare Dataframes    ${html_df}    ${parquet_df}
    ...    df1_name=HTML Table    df2_name=Parquet Dataset
    
    Log    Comparison Report:\n${report}    console=True
    
    Should Be True    ${match}    msg=DataFrames do not match!\n${report}

*** Keywords ***
Open Browser To Report
    [Documentation]    Open Chrome browser and load the HTML report
    ${absolute_path}=    Evaluate    __import__('pathlib').Path(r'${REPORT_FILE}').resolve().as_posix()
    ${report_url}=    Set Variable    file:///${absolute_path}
    Log    Opening URL: ${report_url}    console=True
    Open Browser    ${report_url}    ${BROWSER}
    Maximize Browser Window
    Wait Until Page Contains Element    xpath=//table[@id='results-table']    timeout=10s
    Log    Report loaded successfully    console=True
