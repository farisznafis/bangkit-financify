package com.code.precapstone.view.category

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.code.precapstone.databinding.ActivityCategoryBinding
import com.code.precapstone.view.calculation.CalculationActivity
import com.code.precapstone.view.main.MainActivity

class CategoryActivity : AppCompatActivity() {
    private lateinit var binding: ActivityCategoryBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCategoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.tvBack.setOnClickListener{
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        }

        binding.apply {

            binding.cvCategory1.setOnClickListener{
                val kategoriKendaraanText = binding.tvCarCategory.text.toString()
                startActivity(kategoriKendaraanText)
            }
            binding.cvCategory2.setOnClickListener{
                val kategoriGadgetText = binding.tvPhoneCategory.text.toString()
                startActivity(kategoriGadgetText)
            }
            binding.cvCategory3.setOnClickListener{
                val kategoriPernikahanText = binding.tvMariageCategory.text.toString()
                startActivity(kategoriPernikahanText)
            }
            binding.cvCategory4.setOnClickListener{
                val kategoriTravelingText = binding.tvTravelCategory.text.toString()
                startActivity(kategoriTravelingText)
            }
            binding.cvCategory5.setOnClickListener{
                val kategoriPendidikanText = binding.tvEducationCategory.text.toString()
                startActivity(kategoriPendidikanText)
            }
        }
    }

    fun startActivity(categoryText: String){
        val intent = Intent(this@CategoryActivity, CalculationActivity::class.java)
        intent.putExtra("categoryText", categoryText)
        startActivity(intent)
    }
}