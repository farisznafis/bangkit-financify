package com.code.precapstone.data.response

import com.google.gson.annotations.SerializedName

data class InflationResponse(

	@field:SerializedName("trend")
	val trend: String? = null,

	@field:SerializedName("prediction")
	val prediction: Double? = null,

	@field:SerializedName("time_required")
	val timeRequired: TimeRequired? = null
)

data class TimeRequired(

	@field:SerializedName("remaining_months")
	val remainingMonths: Int? = null,

	@field:SerializedName("years_to_goal")
	val yearsToGoal: Int? = null
)
