from bs4 import BeautifulSoup
from database import Course
import aiohttp

CURRENT_SEMESTER = "202408"


async def fetch_course_details(
    crn: int, session: aiohttp.ClientSession
) -> tuple[Course, list[int]]:
    url = f"https://oscar.gatech.edu/bprod/bwckschd.p_disp_detail_sched?term_in={CURRENT_SEMESTER}&crn_in={crn}"
    async with session.get(url) as response:
        content = await response.text()
        soup = BeautifulSoup(content, "html.parser")
        info_table = soup.find(
            "table",
            class_="datadisplaytable",
            summary="This table is used to present the detailed class information.",
        )
        header = info_table.find("th", class_="ddlabel")
        name, _, course_info, section = header.text.split(" - ")
        subject_code, course_number = course_info.split(" ")

        seat_table = soup.find(
            "table",
            class_="datadisplaytable",
            summary="This layout table is used to present the seating numbers.",
        )
        seat_info = seat_table.find_all("td", class_="dddefault")

    return Course(
        semester=CURRENT_SEMESTER,
        crn=crn,
        name=name,
        subject_code=subject_code,
        course_number=course_number,
        section=section,
    ), [
        int(s)
        for s in [
            seat_info[0].text,
            seat_info[1].text,
            # seat_info[3].text,
            # seat_info[4].text,
        ]
    ]
