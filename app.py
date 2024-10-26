import mysql.connector as sql
import pandas as pd
import plotly.express as px
import streamlit as st
import altair as alt


# Establish the connection
connection = sql.connect(
    host=st.secrets["DB_HOST"],
    port=st.secrets["PORT"],
    user=st.secrets["DB_USER"],
    password=st.secrets["DB_PASSWORD"],
    database=st.secrets["DB_SCHEMA"]
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

    query1B = '''SELECT 
        genre.genreName AS 'Genre',
        app.appName AS 'App Name',
        fact.positiveReviews AS 'Positive Reviews'
        FROM 
            fact_steamgames fact
        JOIN 
            dim_app app ON fact.appSK = app.appSK
        JOIN 
            bridge_genre_group bgg ON fact.genreGroupKey = bgg.genreGroupKey
        JOIN 
            dim_genre genre ON bgg.genreSK = genre.genreSK
        WHERE genre.genreName='{genre}'
        ORDER BY 
            genre.genreName, fact.positiveReviews DESC
        LIMIT 50;
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

with tab4:
    # Load the years from the database
    years = pd.read_sql("SELECT releaseYear FROM dim_year ORDER BY releaseYear", connection)

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


with tab3:
    st.subheader("What were the most popular genres across each year?", divider="gray")
    CCol1, CCol2 = st.columns(2)
    
    with CCol2:
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
        categories = pd.read_sql('''SELECT DISTINCT categoryName
                        FROM dim_category
                        JOIN bridge_category_group ON bridge_category_group.categorySK = dim_category.categorySK
                        JOIN fact_steamgames ON fact_steamgames.categoryGroupKey = bridge_category_group.categoryGroupKey
                        JOIN dim_year ON dim_year.yearSK = fact_steamgames.yearSK
                        WHERE releaseYear="{year}"
                        ORDER BY categoryName ASC;'''.format(year=yearOption), connection)

        if not categories.empty:
            categoryOption = st.selectbox(
                "Select Category:",
                categories['categoryName'].tolist(),
                index=0,  # Ensure index is valid
                placeholder="Enter a category."
            )
        else:
            st.warning("No categories available for the selected year.")

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
            genre.genreSK,
            category.categorySK,
            year.yearSK
        ORDER BY 
            genre.genreName,
            category.categoryName,
            year.releaseYear;
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


connection.close()