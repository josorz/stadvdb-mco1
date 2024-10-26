import mysql.connector as sql
import pandas as pd
import plotly.express as px
import streamlit as st
import altair as alt


# Establish the connection
connection = sql.connect(
    host="localhost",
    user="root",
    password="password",
    database="steam_dw"
)

st.set_page_config(layout="wide")

tab1, tab2, tab3, tab4 = st.tabs(["1", "2", "3A", "3B"])

with tab1:
    st.subheader("Which genres have the most positive reviews?", divider="gray")

    query1A = f'''SELECT 
        g.genreSK, 
        g.genreName, 
        SUM(f.positiveReviews) as 'Total Positive Reviews'
    FROM 
        dim_genre g
    JOIN 
        bridge_genre_group gg ON g.genreSK = gg.genreSK
    JOIN 
        fact_steamgames f ON gg.genreGroupKey = f.genreGroupKey
    GROUP BY
        g.genreSK
    ORDER BY 
        SUM(f.positiveReviews) DESC;'''
    
    df = pd.read_sql(query1A, connection)
    df["Total Positive Reviews"] = pd.to_numeric(df["Total Positive Reviews"])
    df = df.rename(columns={"genreName": "Genre Name"}).sort_values(by=['Total Positive Reviews'], ascending=False)

    columns_to_display = ['Genre Name', 'Total Positive Reviews'] 
    df_selected = df[columns_to_display]
    df_selected.index += 1

    ACol1, ACol2 = st.columns(2)

    with ACol1:
        st.dataframe(df_selected, use_container_width=True)

    with ACol2:
        fig = px.pie(df, values='Total Positive Reviews', names='Genre Name', title="Review Distribution")
        st.plotly_chart(fig)

    st.subheader("Given a genre, what are its most positively reviewed games?")
    option = st.selectbox(
        "Select Genre",
        (df.loc[:,["Genre Name"]]),
        index=0,
        placeholder="Select genre...",
    )

    query1B = '''SELECT DISTINCT temp.Genre, temp.AppName AS 'App Name', temp.PosReviews AS 'Total Positive Reviews'
    FROM (
        SELECT
            (SELECT genreName
            FROM dim_genre
            WHERE genreSK = gg.genreSK) AS Genre,
            (SELECT appName
            FROM dim_app
            WHERE appSK = f.appSK) AS AppName,
            f.positiveReviews AS PosReviews
        FROM fact_steamgames f
        LEFT JOIN (
            SELECT *
            FROM bridge_genre_group
            WHERE genreGroupKey IN (
                SELECT genreGroupKey
                FROM bridge_genre_group
            )
        ) gg ON f.genreGroupKey = gg.genreGroupKey
        CROSS JOIN dim_genre g
        WHERE g.genreSK = gg.genreSK
    ) temp
    WHERE UPPER(TRIM(temp.Genre)) = UPPER(TRIM(temp.Genre))
    AND temp.Genre="{genre}"
    ORDER BY temp.PosReviews DESC
    LIMIT 50
    '''.format(genre=option)
    df1b = pd.read_sql(query1B, connection)
    df1b = df1b.drop(columns=["Genre"])
    df1b.index += 1
    st.dataframe(df1b, use_container_width=True)

with tab2:
    st.subheader("What were the most played categories in the last two weeks?", divider="gray")

    query2A = f'''SELECT 
        category.categoryName AS 'Category',
        AVG(fact.averagePlayTime_twoWeeks) AS 'Average Playtime (Two Weeks)'
    FROM 
        fact_steamgames fact
    JOIN 
        bridge_category_group bcg ON fact.categoryGroupKey = bcg.categoryGroupKey
    JOIN 
        dim_category category ON bcg.categorySK = category.categorySK
    GROUP BY 
        category.categorySK
    ORDER BY 
        AVG(fact.averagePlayTime_twoWeeks) DESC;
    '''
    df = pd.read_sql(query2A, connection)

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Category', sort=None),
        y='Average Playtime (Two Weeks)'
    ).properties(
        title="Average Playtime (Two Weeks) by Category"
    )

    # Display chart in Streamlit
    st.altair_chart(chart, use_container_width=True)

    query2B = f'''SELECT AVG(f.averagePlayTime_twoWeeks) as "Average Playing time across all categories"
    FROM dim_category c
    LEFT JOIN bridge_category_group cg
    ON c.categorySK = cg.categorySK
    LEFT JOIN fact_steamgames f
    ON cg.categoryGroupKey = f.categoryGroupKey;
    '''
    results = pd.read_sql(query2B, connection)

    st.caption("An average of " + str(results.iloc[0]['Average Playing time across all categories']) + " hours were played across all categories.")

with tab3:
    st.subheader("What were the most popular genres across each year?", divider="gray")
    CCol1, CCol2 = st.columns(2)
    with CCol1:

        query3A = f'''SELECT 
            genre.genreName AS 'Genre',
            category.categoryName AS 'Category',
            year.releaseYear AS 'Year',
            COUNT(fact.appSK) AS 'Number of Apps Developed'
        FROM 
            fact_steamgames fact
        JOIN 
            bridge_genre_group bgg ON fact.genreGroupKey = bgg.genreGroupKey
        JOIN 
            dim_genre genre ON bgg.genreSK = genre.genreSK
        JOIN 
            bridge_category_group bcg ON fact.categoryGroupKey = bcg.categoryGroupKey
        JOIN 
            dim_category category ON bcg.categorySK = category.categorySK
        JOIN 
            dim_year year ON fact.yearSK = year.yearSK
        GROUP BY 
            genre.genreName,
            category.categoryName,
            year.releaseYear
        ORDER BY 
            genre.genreName,
            category.categoryName,
            year.releaseYear;
        ;
        '''
        df = pd.read_sql(query3A, connection)

        # Ensure 'Year' is treated as a categorical variable
        df['Year'] = pd.to_datetime(df['Year'], format='%Y').dt.year

        # Create the selectbox for year selection

        # Create the density heatmap
        fig = px.density_heatmap(
            df, 
            x="Category", 
            y="Genre", 
            z="Number of Apps Developed", 
            color_continuous_scale="Reds",
            title="Review Distribution by Genre and Category, 1997-Present"
        )

        # Update figure layout
        fig.update(layout_coloraxis_showscale=False)
        fig.update_layout(height=600)


        st.plotly_chart(fig, use_container_width=True)

    with CCol2:
        # Load the years from the database
        years = pd.read_sql("SELECT releaseYear FROM dim_year ORDER BY releaseYear", connection)

        # Convert years to a list
        years_list = years['releaseYear'].tolist()

        # Year selection dropdown
        yearOption = st.selectbox(
            "Select Year:",
            years_list,
            index=0,  # Set to a valid index based on your years_list
            placeholder="Enter a year."
        )

        # Load categories from the database
        categories = pd.read_sql("SELECT categoryName FROM dim_category ORDER BY categoryName", connection)

        # Assuming df is properly initialized with relevant data
        # df = pd.read_sql("SELECT * FROM your_data_table", connection)  # Example initialization

        # Check if df is available and contains the right columns
        if 'Year' in df.columns and 'Category' in df.columns:
            # Define category options based on the selected year
            category_options = df[df['Year'] == yearOption]['Category'].unique().tolist()

            # Ensure there are categories available for the selected year
            if category_options:
                categoryOption = st.selectbox(
                    "Select Category:",
                    category_options,
                    index=0,  # Ensure index is valid
                    placeholder="Enter a category."
                )
            else:
                st.warning("No categories available for the selected year.")
        else:
            st.error("DataFrame does not contain 'Year' or 'Category' columns.")
        query3B = '''SELECT 
            genre.genreName AS 'Genre',
            COUNT(DISTINCT app.appSK) AS 'Number of Apps'
        FROM 
            fact_steamgames fact
        JOIN 
            dim_app app ON fact.appSK = app.appSK
        JOIN 
            bridge_category_group bcg ON fact.categoryGroupKey = bcg.categoryGroupKey
        JOIN 
            dim_category category ON bcg.categorySK = category.categorySK
        JOIN 
            bridge_genre_group bgg ON fact.genreGroupKey = bgg.genreGroupKey
        JOIN 
            dim_genre genre ON bgg.genreSK = genre.genreSK
        JOIN 
            dim_year year ON fact.yearSK = year.yearSK
        WHERE 
            year.releaseYear = '{Year}'
            AND category.categoryName = '{Category}'
        GROUP BY 
            genre.genreName
        ORDER BY 
            COUNT(DISTINCT app.appSK) DESC
        LIMIT 10;
        '''.format(Year=yearOption, Category=categoryOption)

        df = pd.read_sql(query3B, connection)
        df.index += 1
        st.dataframe(df, use_container_width=True)


with tab4:
    st.write("What are the most active genres between two years?")
    options = years['releaseYear'].tolist()
    start_year, end_year = st.select_slider(
        "Year Range",
        options=options,
        value=(options[0], options[-1]),
    )

    query3C = '''SELECT 
        genre.genreName AS 'Genre',
        COUNT(app.appSK) AS 'Number of Apps'
    FROM 
        fact_steamgames fact
    JOIN 
        dim_app app ON fact.appSK = app.appSK
    JOIN 
        bridge_genre_group bgg ON fact.genreGroupKey = bgg.genreGroupKey
    JOIN 
        dim_genre genre ON bgg.genreSK = genre.genreSK
    JOIN 
        dim_year year ON fact.yearSK = year.yearSK
    WHERE 
        year.releaseYear BETWEEN "{start_year}" AND "{end_year}"
    GROUP BY 
        genre.genreName
    ORDER BY 
        COUNT(app.appSK) DESC
    LIMIT 10;
    '''.format(start_year=start_year, end_year=end_year)

    df = pd.read_sql(query3C, connection)
    df = df.sort_values(by="Number of Apps", ascending=False)

    title = "Distribution of New Steam Games by Genre (" + str(start_year)
    if start_year != end_year:
        title += " - "+ str(end_year) + ")"

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Genre', sort=None),
        y='Number of Apps'
    ).properties(
        title=title
    )

    # Display chart in Streamlit
    st.altair_chart(chart, use_container_width=True)

connection.close()