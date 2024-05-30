from groq import Groq
from openai import OpenAI
from routes.metadata.run_md_query import run_md_query as get_location
from routes.docs.search import run_rag_pipeline as get_information
import os
from strictjson import *
from routes.llm_connections import openai_client
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_persona_from_query(query: str):
    """
    This function returns the persona of the user based on the query
    """
    persona_system_prompt = """Identify the persona of the user based on the query provided by the user.Possible personas include: single_person, couple, couple_with_children, general, multi-generational_family_couple_with_parents_and_children, elderly_couple, differently_abled. Respond with JSON like : 
        {
            "persona" : "couple"
        }
    """
    res = strict_json(system_prompt = persona_system_prompt,
                    user_prompt = query,
                    output_format ={
                                    'persona' : 'persona of customer'
                                },
                    llm = llm)
    

    persona = res['persona']
    print(persona)

    
    if persona == 'single_person':
        location_query = 'Focus on location positives - retail, dining, bars, entertainment, mass transit, connectivity'
        amenities_query = 'Focus on amenities - sports, fitness, cleaning & maintenance, concierge services'
        design_construction = 'Design - Flexibility inside the unit, ready-to-move-in, smart home features'
        unit_recommended = '1 or 2 bed units'
    elif persona == 'couple':
        location_query = 'Focus on location positives - retail, dining, bars, entertainment, mass transit, connectivity'
        amenities_query = 'Focus on amenities - sports, fitness, cleaning & maintenance, concierge services'
        design_construction = 'Design - Flexibility inside the unit, ready-to-move-in, smart home features'
        unit_recommended = '1 or 2 bed units'
    elif persona == 'couple_with_children':
        location_query = 'Focus on location positives - retail, dining, entertainment, connectivity, schools, childrens entertainment centers nearby'
        amenities_query = 'Focus on amenities - sports, fitness, play areas for children, gardens for children'
        design_construction = 'Design - Study spaces, helper/staff room, balconies, walk-in closet, smart home features'
        unit_recommended = '2 bed units'
    elif persona == 'multi-generational_family_couple_with_parents_and_children':
        location_query = 'Focus on location positives - schools, parks, family-friendly activities, safety, community'
        amenities_query = 'Focus on amenities - sports, fitness, play areas for children, gardens for elderly, medical center'
        design_construction = 'Design - Ease of movement, safety features, anti-slip flooring, grab bars, ramps'
        unit_recommended = '4 bed units'
    elif persona == 'elderly_couple':
        location_query = 'Focus on location positives - retail, healthcare, parks & greenery, safety, air quality, walkability'
        amenities_query = 'Focus on amenities - green spaces, health facilities, medical provisions, sports amenities'
        design_construction = 'Design - Ease of movement, safety features, anti-slip flooring, grab bars, ramps'
        unit_recommended = '1 or 2 bed units'
    elif persona == 'differently_abled':
        location_query = 'Focus on location positives - retail, dining, bars, entertainment, mass transit, connectivity'
        amenities_query = 'Focus on amenities - accessibility related design features, ramps, wheel chair friendly, braille-friendly elevators'
        design_construction = 'Design – Accessibility within the unit, large bathrooms with hand rails, uniform level flooring'
        unit_recommended = '1 or 2 bed units'
    
    return {
        "persona": persona,
        "location_query": location_query,
        "amenities_query": amenities_query,
        "design_construction": design_construction,
        "unit_recommended": unit_recommended
    }


def get_pitch_from_persona(persona : dict, project_id: str, user_query: str):
    """
    This function returns the pitch based on the persona
    """
    try:
        futures = []
        with ThreadPoolExecutor() as executor:
            # Submit tasks to the executor
            futures.append(executor.submit(get_location, project_id, persona['location_query']))
            futures.append(executor.submit(get_information, project_id, persona['amenities_query']))
            futures.append(executor.submit(get_information, project_id, persona['design_construction']))

            location = futures[0].result()
            location_query = location.get('answer',"")
            print(f'Location query: {location_query}')

            amenities = futures[1].result()
            amenities_query = amenities.get('answer','')
            print(f'Amenities query: {amenities_query}')
            

            design = futures[2].result()
            design_construction = design.get('answer',"")
            print(f'Design query: {design_construction}')
        

        unit_recommendation = persona['unit_recommended']
        print(unit_recommendation)

        prompt = f"""
            Write a detailed pitch in less than 400 words for a residential project that integrates project details, floor plan details, location details, and sales details. The pitch should include the following sections and address each type of buyer demographic:

            Opening Statement: Brief introduction to the project.
            Location Positives: Highlight the advantages of the project's location. {location_query}

            Unit Recommendation: {unit_recommendation}

            Amenities/Master-plan: 
            {amenities_query}

            Design & Construction Positives: {design_construction}

            Mortgage Query: Address common mortgage-related questions and provide relevant information.

            Closing Note: Summarize the key points and encourage the potential buyer to take the next steps.


            Example Prompt:

            "Customer is a family of 3, with 1 toddler. Write a crisp pitch highlighting the location and amenities for kids."

            Example Output:

            Welcome to [Project Name], a premium residential community designed to provide the perfect living environment for families. Nestled in the heart of [Location], this project offers a harmonious blend of luxury, convenience, and community living.

            Our project is strategically located near top-rated schools, ensuring your children have access to quality education just minutes away. The proximity to major office hubs makes commuting a breeze, while the nearby retail and dining options provide endless entertainment possibilities for the entire family.

            For a family of three with a toddler, we recommend our spacious 2-bedroom units, which offer ample space for your family to grow. These units feature a dedicated study space and a large balcony, perfect for enjoying the outdoors.

            [Project Name] boasts a range of family-friendly amenities, including dedicated play areas for children, beautifully landscaped gardens, and state-of-the-art fitness facilities. Our secure, gated community also offers 24/7 concierge services to cater to all your needs.

            Each unit is equipped with premium finishes and modern appliances, ensuring a comfortable and stylish living experience. Our smart home features provide added convenience and security, allowing you to control various aspects of your home with ease.

            Designed with families in mind, our units offer high privacy, flexible living spaces, and thoughtful design elements such as study rooms and ample storage. The construction quality ensures a safe and durable home for years to come.

            We offer competitive pricing, flexible payment plans, and attractive mortgage options to make your dream home a reality. Additionally, we provide exclusive discounts for early buyers and special financial benefits for families.

            Our team of mortgage specialists is available to answer any questions you may have and guide you through the mortgage process, ensuring a smooth and hassle-free experience.

            We invite you to visit [Project Name] and experience the perfect family living environment. Contact us today to schedule a tour and learn more about our exciting offers. Don't miss the opportunity to make [Project Name] your new home.
                
        """


        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_query}
            ],
            temperature=0.5,
            max_tokens=4096,
            top_p=1
        )
        pitch = response.choices[0].message.content
        print(pitch)
        return {'success': True, 'answer': pitch}
    except Exception as e:
        return {'success': False, 'failure': e}

def llm(system_prompt: str, user_prompt: str):
    # ensure your LLM imports are all within this function
    from groq import Groq

    # define your own LLM here
    client = Groq(api_key=os.environ['GROQ_API_KEY'])
    MODEL = 'llama3-70b-8192'

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content