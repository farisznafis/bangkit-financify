package com.code.precapstone.view.calculation

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import com.code.precapstone.R
import com.code.precapstone.databinding.ActivityCalculationBinding
import com.code.precapstone.view.category.CategoryActivity

class CalculationActivity : AppCompatActivity() {
    private lateinit var binding: ActivityCalculationBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCalculationBinding.inflate(layoutInflater)
        setContentView(binding.root)


        binding.apply {
            binding.tvBack.setOnClickListener{
                val intent = Intent(this@CalculationActivity, CategoryActivity::class.java)
                startActivity(intent)
            }

            binding.buttonCalculate.setOnClickListener {
                //TODO
            }
        }
    }
}